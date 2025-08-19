'''Module to check the readiness of the stored information'''
import requests
import redis
from app.opensense import get_temperature
from app.config import create_redis_client

redis_client, REDIS_AVAILABLE = create_redis_client()

def check_caching():
    '''Check if caching content is older than 5 minutes'''
    if not REDIS_AVAILABLE:
        return True

    try:
        cache_key = "temperature_data"
        ttl = redis_client.ttl(cache_key)

        if ttl in (-2, -1):
            return True

        return False
    except redis.RedisError as e:
        print(f"Redis error while checking cache: {e}")
        return True

def reachable_boxes():
    '''Check if more than 50% of sensor boxes are reachable'''
    try:
        _, sensor_stats = get_temperature()
        total_boxes = sensor_stats.get('total', 0)
        reachable = sensor_stats.get('reachable', 0)

        if total_boxes == 0:
            return 400

        percentage = (reachable / total_boxes) * 100

        if percentage > 50:
            return 200
        return 400

    except requests.exceptions.RequestException as e:
        # Handle network-related errors from the API call
        print(f"Network error checking reachable boxes: {e}")
        return 200
    except redis.RedisError as e:
        # Handle Redis-related errors
        print(f"Redis error checking reachable boxes: {e}")
        return 200
    except (ValueError, TypeError, KeyError) as e:
        # Handle data parsing errors
        print(f"Data error checking reachable boxes: {e}")
        return 400

def readiness_check():
    '''Combined readiness check for the /readyz endpoint'''
    try:
        boxes_status = reachable_boxes()
        cache_is_old = check_caching()

        # Only fail if BOTH conditions are bad
        if boxes_status == 400 and cache_is_old:
            return 503

        return 200
    except redis.RedisError as e:
        # If Redis is completely unavailable, still allow the service to be ready
        print(f"Redis error during readiness check: {e}")
        return 200
