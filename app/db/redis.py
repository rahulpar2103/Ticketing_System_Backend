import redis
from app.core.config import settings

redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

def delete_by_prefix(prefix: str):
    try:
        cursor = 0
        while True:
            cursor, keys = redis_client.scan(cursor, match=f"{prefix}*")
            if keys:
                redis_client.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        pass
    
def safe_get(key: str) -> str | None:
    try:
        return redis_client.get(key)
    except Exception:
        return None

def safe_setex(key: str, ttl: int, value: str) -> None:
    try:
        redis_client.setex(key, ttl, value)
    except Exception:
        pass  # cache write failure is non-fatal

def safe_delete(key: str) -> None:
    try:
        redis_client.delete(key)
    except Exception:
        pass