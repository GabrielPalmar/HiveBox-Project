'''Module to get entries from OpenSenseMap API and get the average temperature'''
from datetime import datetime, timezone, timedelta
import os
import requests
import redis

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_DB = int(os.environ.get('REDIS_DB', 0))
CACHE_TTL = int(os.environ.get('CACHE_TTL', 300))

try:
    redis_client = redis.StrictRedis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=240,
        socket_timeout=240
        )

    redis_client.ping()
    REDIS_AVAILABLE = True
    print("Connected to Redis successfully!")
except (redis.ConnectionError, redis.TimeoutError) as e:
    REDIS_AVAILABLE = False
    print("Could not connect to Redis.")

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
    time_iso = datetime.now(timezone.utc) - timedelta(hours=1).isoformat().replace("+00:00", "Z")

    params = {
        "date": time_iso,
        "format": "json"
    }

    print('Getting data from OpenSenseMap API...')

    response = requests.get("https://api.opensensemap.org/boxes", params=params, timeout=240)
    print('Data retrieved successfully!')

    res = [d.get('sensors') for d in response.json() if 'sensors' in d]

    temp_list = []

    for sensor_list in res:
        for measure in sensor_list:
            if measure.get('title') == "Temperatur" and 'lastMeasurement' in measure:
                last_measurement = measure['lastMeasurement']
                if last_measurement is not None and 'value' in last_measurement:
                    last_measurement_int = float(last_measurement['value'])
                    temp_list.append(last_measurement_int)

    total_sum = sum(temp_list)
    average = total_sum / len(temp_list) if temp_list else 0

    if average <= 10:
        result = f'Average temperature: {average:.2f} °C (Warning: Too cold)\n'
    elif 10 < average <= 36:
        result = f'Average temperature: {average:.2f} °C (Good)\n'
    else:
        result = f'Average temperature: {average:.2f} °C (Warning: Too hot)\n'

    if REDIS_AVAILABLE:
        try:
            redis_client.setex(cache_key, CACHE_TTL, result)
            print("Data cached in Redis.")
        except redis.RedisError as e:
            print(f"Redis error while caching data: {e}")

    return result
