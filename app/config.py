'''Shared configuration module'''
import os
import redis

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_DB = int(os.environ.get('REDIS_DB', 0))
CACHE_TTL = int(os.environ.get('CACHE_TTL', 300))

def create_redis_client():
    '''Create and return Redis client with error handling'''
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
        print("Connected to Redis successfully!")
        return redis_client, True
    except (redis.ConnectionError, redis.TimeoutError) as e:
        print(f"Could not connect to Redis: {e}")
        return None, False
