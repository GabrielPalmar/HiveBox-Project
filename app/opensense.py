'''Module to get entries from OpenSenseMap API and get the average temperature'''
from datetime import datetime, timezone, timedelta
import json
import requests
import redis
from app.config import create_redis_client, CACHE_TTL

# Use shared Redis client
redis_client, REDIS_AVAILABLE = create_redis_client()

_sensor_stats = {"total_sensors": 0, "null_count": 0}

def classify_temperature(average):
    '''Classify temperature based on ranges using dictionary approach'''
    # Define temperature ranges and their classifications
    temp_classifications = {
        "cold": (float('-inf'), 10, "Warning: Too cold"),
        "good": (10, 36, "Good"), 
        "hot": (36, float('inf'), "Warning: Too hot")
    }

    # Find the appropriate classification
    for _, (min_temp, max_temp, status) in temp_classifications.items():
        if min_temp < average <= max_temp:
            return status

    return "Unknown"  # Default case

def _parse_partial_json_array(text: str):
    """Parse as many full objects as possible from a (possibly truncated) JSON array."""
    decoder = json.JSONDecoder()
    items = []
    i = text.find('[')
    if i == -1:
        return items
    i += 1  # past '['
    n = len(text)
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if i >= n or text[i] == ']':
            break
        try:
            obj, end = decoder.raw_decode(text, i)
        except json.JSONDecodeError:
            # truncated object at the end; stop with what we have
            break
        items.append(obj)
        i = end
        while i < n and text[i].isspace():
            i += 1
        if i < n and text[i] == ',':
            i += 1
    return items

def get_temperature():
    '''Function to get the average temperature from OpenSenseMap API.'''
    if REDIS_AVAILABLE:
        try:
            cached_data = redis_client.get("temperature_data")
            if cached_data:
                print("Using cached data from Redis.")
                cached_result = cached_data.decode('utf-8')
                default_stats = {"total_sensors": 0, "null_count": 0}
                return cached_result, default_stats
        except redis.RedisError as e:
            print(f"Redis error: {e}. Proceeding without cache.")

    print("Fetching new data from OpenSenseMap API...")

    # Ensuring that data is not older than 1 hour.
    time_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")

    params = {
        "date": time_iso,
        "format": "json"
    }

    # Streaming configuration
    max_mb = 0.5
    max_bytes = int(max_mb * 1024 * 1024)

    print('Getting data from OpenSenseMap API...')

    try:
        # Stream the response and count bytes
        response = requests.get(
            "https://api.opensensemap.org/boxes",
            params=params,
            stream=True,
            timeout=(180, 60)
        )
        response.raise_for_status()

        downloaded = 0
        chunks = []
        truncated = False

        for chunk in response.iter_content(chunk_size=64 * 1024):  # 64 KB
            if not chunk:
                break
            chunks.append(chunk)
            downloaded += len(chunk)
            if downloaded >= max_bytes:
                print(f"Reached {max_mb} MB limit ({downloaded:,} bytes), stopping download")
                truncated = True
                response.close()
                break

        print(f'Bytes downloaded: {downloaded:,}')
        print('Data retrieved successfully!' + (" (partial)" if truncated else ""))

        # Build body and parse JSON
        body = b"".join(chunks)
        text = body.decode(response.encoding or "utf-8", errors="replace")

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            if not truncated:
                print("Warning: Unexpected JSON parse error. Trying partial parse.")
            data = _parse_partial_json_array(text)
            if not data:
                return "Error: Failed to parse JSON and no partial objects found\n", {
                    "total_sensors": 0,
                    "null_count": 0
                    }

    except requests.Timeout:
        print("API request timed out")
        return "Error: API request timed out\n", {"total_sensors": 0, "null_count": 0}
    except requests.RequestException as e:
        print(f"API request failed: {e}")
        return f"Error: API request failed - {e}\n", {"total_sensors": 0, "null_count": 0}

    # Process the data (keeping the existing logic)
    _sensor_stats["total_sensors"] = sum(1 for d in data if isinstance(d, dict) and "sensors" in d)
    res = [d.get('sensors') for d in data if isinstance(d, dict) and 'sensors' in d]

    temp_list = []
    _sensor_stats["null_count"] = 0

    for sensor_list in res:
        for measure in sensor_list:
            if measure.get('unit') == "°C" and 'lastMeasurement' in measure:
                last = measure['lastMeasurement']
                if last is not None and isinstance(last, dict) and 'value' in last:
                    try:
                        temp_list.append(float(last['value']))
                    except (TypeError, ValueError):
                        _sensor_stats["null_count"] += 1
                else:
                    _sensor_stats["null_count"] += 1

    average = sum(temp_list) / len(temp_list) if temp_list else 0.0

    if not temp_list:
        print("Warning: No valid temperature readings found")

    # Use the dictionary-based classification
    status = classify_temperature(average)
    result = f'Average temperature: {average:.2f} °C ({status})\n'

    if REDIS_AVAILABLE:
        try:
            redis_client.setex("temperature_data", CACHE_TTL, result)
            print("Data cached in Redis.")
        except redis.RedisError as e:
            print(f"Redis error while caching data: {e}")

    return result, _sensor_stats
