import redis
from app.core.config import settings

redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

def delete_by_prefix(prefix: str):
    cursor = 0
    while True:
        cursor, keys = redis_client.scan(cursor, match=f"{prefix}*")
        if keys:
            redis_client.delete(*keys)
        if cursor == 0:
            break