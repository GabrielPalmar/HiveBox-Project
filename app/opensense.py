'''Module to get entries from OpenSenseMap API and get the average temperature'''
from datetime import datetime, timezone, timedelta
import re
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

def get_temperature():
    '''Function to get the average temperature from OpenSenseMap API.'''
    cache_key = "temperature_data"
    if REDIS_AVAILABLE:
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                print("Using cached data from Redis.")
                return cached_data
        except redis.RedisError as e:
            print(f"Redis error: {e}. Proceeding without cache.")

    print("Fetching new data from OpenSenseMap API...")

    # Ensuring that data is not older than 1 hour.
    time_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")

    params = {
        "date": time_iso,
        "format": "json"
    }

    print('Getting data from OpenSenseMap API...')

    response = requests.get("https://api.opensensemap.org/boxes", params=params, timeout=300)
    print('Data retrieved successfully!')

    _sensor_stats["total_sensors"] = sum(
        1 for line in response.text.splitlines() if re.search(r'^\s*"sensors"\s*:\s*\[', line)
    )

    res = [d.get('sensors') for d in response.json() if 'sensors' in d]

    temp_list = []
    _sensor_stats["null_count"] = 0  # Initialize counter for null measurements

    for sensor_list in res:
        for measure in sensor_list:
            if measure.get('unit') == "\u00b0C" and 'lastMeasurement' in measure:
                last_measurement = measure['lastMeasurement']
                if last_measurement is not None and 'value' in last_measurement:
                    last_measurement_int = float(last_measurement['value'])
                    temp_list.append(last_measurement_int)
                else:
                    _sensor_stats["null_count"] += 1

    total_sum = sum(temp_list)
    average = total_sum / len(temp_list) if temp_list else 0

    # Use the dictionary-based classification
    status = classify_temperature(average)
    result = f'Average temperature: {average:.2f} °C ({status})\n'

    if REDIS_AVAILABLE:
        try:
            redis_client.setex(cache_key, CACHE_TTL, result)
            print("Data cached in Redis.")
        except redis.RedisError as e:
            print(f"Redis error while caching data: {e}")

    return result, _sensor_stats
