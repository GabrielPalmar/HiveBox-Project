'''Module to check the readiness of the stored information'''
import os
from opensense import get_temperature
import redis

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_DB = int(os.environ.get('REDIS_DB', 0))

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

def check_caching():
    '''Check if caching content is older than 5 minutes'''
    if not REDIS_AVAILABLE:
        return False

    # Get the TTL (time to live) of the cached temperature data
    cache_key = "temperature_data"
    ttl = redis_client.ttl(cache_key)

    if ttl == -2:  # Key doesn't exist (expired)
        return True
    elif ttl == -1:  # Key exists but has no expiry
        return True
    elif ttl <= (5 * 60) and ttl > 0:  # Cache exists and has time remaining (valid)
        return False

    return True

def reachable_boxes():
    '''Check if 50% + 1 of boxes are reachable'''
    _, sensor_stats = get_temperature()
    total = sensor_stats["total_sensors"]
    null_count = sensor_stats["null_count"]
    if total > 0 and null_count > (total * 0.5):
        print("Warning: More than 50% of sensors are unreachable")
        return 400
    return 200

def readiness_check():
    '''Combined readiness check for the /readyz endpoint'''
    boxes_status = reachable_boxes()
    cache_valid = check_caching()

    # Return 503 if BOTH conditions are met:
    # 1. More than 50% of boxes are unreachable AND
    # 2. Cache is older than 5 minutes
    if boxes_status == 400 and cache_valid:
        return 503

    return 200
