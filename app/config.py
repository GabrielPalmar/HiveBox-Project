'''Shared configuration module'''
from typing import Tuple, Optional
import os
import redis

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_DB = int(os.environ.get('REDIS_DB', 0))
CACHE_TTL = int(os.environ.get('CACHE_TTL', 300))

def create_redis_client() -> Tuple[Optional[redis.Redis], bool]:
    """Create Redis client and return it with availability status."""
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True
        )
        client.ping()  # Test connection
        print("Connected to Redis successfully!")
        return client, True
    except (redis.ConnectionError, redis.TimeoutError) as e:
        print(f"Could not connect to Redis: {e}")
        return None, False
