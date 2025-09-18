'''Module to check the readiness of the stored information'''
import json
import requests
import redis
from app.opensense import get_temperature, REDIS_CLIENT
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
        total_boxes = sensor_stats.get('total_sensors', 0)
        unreachable = sensor_stats.get('null_count', 0)

        # No sensors configured => treat as healthy
        if total_boxes == 0:
            return 200

        percentage_unreachable = (unreachable / total_boxes) * 100

        # Fail only if strictly more than 50% are unreachable
        if percentage_unreachable > 50:
            return 400
        return 200

    except (json.JSONDecodeError, requests.exceptions.RequestException, redis.RedisError) as e:
        print(f"Error checking reachable boxes: {e}")
        return 200
    except (ValueError, TypeError, KeyError) as e:
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

def check_redis():
    '''Function to check Redis is Up'''
    if REDIS_CLIENT:
        try:
            if REDIS_CLIENT.ping():
                return '<p>Redis is available &#10004;</p>', True

            return '<p>Redis ping failed &#10060;</p>', False

        except redis.RedisError as e:
            return f'<p>Redis connection failed &#10060;: {e}</p>', False
    else:
        return '<p>Redis is not configured &#10060;</p>', False
