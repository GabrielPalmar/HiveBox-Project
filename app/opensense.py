'''Module to get entries from OpenSenseMap API and get the average temperature'''
import requests
import redis
import ijson
from datetime import datetime, timezone, timedelta
from app.config import create_redis_client, CACHE_TTL

redis_client, REDIS_AVAILABLE = create_redis_client()

_sensor_stats = {"total_sensors": 0, "null_count": 0}

def classify_temperature(average):
    '''Classify temperature based on ranges using dictionary approach'''
    temp_classifications = {
        "cold": (float('-inf'), 10, "Warning: Too cold"),
        "good": (10, 36, "Good"),
        "hot": (36, float('inf'), "Warning: Too hot"),
    }
    for _, (min_temp, max_temp, status) in temp_classifications.items():
        if min_temp < average <= max_temp:
            return status
    return "Unknown"

def get_temperature():
    '''Function to get the average temperature from OpenSenseMap API.'''
    if REDIS_AVAILABLE:
        try:
            cached_data = redis_client.get("temperature_data")
            if cached_data:
                default_stats = {"total_sensors": 0, "null_count": 0}
                cached_str = cached_data.decode("utf-8") if isinstance(cached_data, (bytes, bytearray)) else cached_data
                return cached_str, default_stats
        except redis.RedisError:
            pass

    # Ensuring that data is not older than 1 hour.
    time_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    params = {"date": time_iso, "format": "json"}

    try:
        response = requests.get(
            "https://api.opensensemap.org/boxes",
            params=params,
            stream=True,
            timeout=(60, 90)  # (connect, read)
        )
        if hasattr(response, "raise_for_status"):
            response.raise_for_status()
        if hasattr(response, "raw") and hasattr(response.raw, "decode_content"):
            response.raw.decode_content = True
    except requests.Timeout:
        return "Error: API request timed out\n", {"total_sensors": 0, "null_count": 0}
    except requests.RequestException as e:
        return f"Error: API request failed - {e}\n", {"total_sensors": 0, "null_count": 0}

    temp_sum = 0.0
    temp_count = 0
    sensor_count = 0
    _sensor_stats["null_count"] = 0

    try:
        if hasattr(response, "raw") and response.raw:
            # Stream parse with ijson
            for sensor in ijson.items(response.raw, 'item.sensors.item'):
                sensor_count += 1
                if sensor.get('unit') == "°C" and 'lastMeasurement' in sensor:
                    last = sensor.get('lastMeasurement')
                    if last is not None and 'value' in last:
                        try:
                            temp_sum += float(last['value'])
                            temp_count += 1
                        except (TypeError, ValueError):
                            _sensor_stats["null_count"] += 1
                    else:
                        _sensor_stats["null_count"] += 1
        else:
            # Fallback for mocks/tests without .raw
            boxes = response.json()
            for box in boxes:
                sensors = box.get("sensors", [])
                for sensor in sensors:
                    sensor_count += 1
                    if sensor.get('unit') == "°C" and 'lastMeasurement' in sensor:
                        last = sensor.get('lastMeasurement')
                        if last is not None and 'value' in last:
                            try:
                                temp_sum += float(last['value'])
                                temp_count += 1
                            except (TypeError, ValueError):
                                _sensor_stats["null_count"] += 1
                        else:
                            _sensor_stats["null_count"] += 1
    except Exception as e:
        return f"Error: parse failed - {e}\n", {"total_sensors": 0, "null_count": 0}

    _sensor_stats["total_sensors"] = sensor_count
    average = (temp_sum / temp_count) if temp_count else 0.0
    status = classify_temperature(average)
    result = f'Average temperature: {average:.2f} °C ({status})\n'

    if REDIS_AVAILABLE:
        try:
            redis_client.setex("temperature_data", CACHE_TTL, result)
        except redis.RedisError:
            pass

    return result, _sensor_stats
