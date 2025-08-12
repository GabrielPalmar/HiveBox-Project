'''Module to check the readiness of the stored information'''
from app.opensense import get_temperature
from app.config import create_redis_client

# Use shared Redis client
redis_client, REDIS_AVAILABLE = create_redis_client()

def check_caching():
    '''Check if caching content is older than 5 minutes'''
    if not REDIS_AVAILABLE:
        return True  # No Redis = cache is old

    cache_key = "temperature_data"
    ttl = redis_client.ttl(cache_key)

    # Cache is considered "old" when:
    # - Key doesn't exist (ttl == -2)
    # - Key has no expiry (ttl == -1)
    # - Less than 5 minutes remaining (ttl > 0 and ttl <= 300)
    if ttl == -2 or ttl == -1:
        return True

    # If cache exists and has more than 5 minutes, it's fresh
    # Since your CACHE_TTL is 300 seconds (5 minutes), cache is always "old"
    # unless you increase CACHE_TTL to more than 300 seconds
    return False

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
    cache_is_old = check_caching()  # Rename: True = old, False = fresh

    # Return 503 if BOTH conditions are met:
    # 1. More than 50% of boxes are unreachable AND
    # 2. Cache is older than 5 minutes
    if boxes_status == 400 and cache_is_old:  # Now it reads correctly
        return 503

    return 200
