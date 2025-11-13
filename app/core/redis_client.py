# app/core/redis_client.py
import redis
from app.core.config import settings

redis_client = redis.Redis(
    host=settings.REDIS_HOST or "localhost",
    port=int(settings.REDIS_PORT or 6379),
    db=int(settings.REDIS_DB or 1),
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True
)