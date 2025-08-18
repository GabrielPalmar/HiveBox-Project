'''Module to check the readiness of the stored information'''
from app.opensense import get_temperature
from app.config import create_redis_client

redis_client, REDIS_AVAILABLE = create_redis_client()

def check_caching():
    '''Check if caching content is older than 5 minutes'''
    if not REDIS_AVAILABLE:
        return True

    cache_key = "temperature_data"
    ttl = redis_client.ttl(cache_key)

    if ttl in (-2, -1):
        return True

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
    cache_is_old = check_caching()

    if boxes_status == 400 and cache_is_old:
        return 503

    return 200
