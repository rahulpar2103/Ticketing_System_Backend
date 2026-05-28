import ssl
from celery import Celery
from app.core.config import settings

redis_url = settings.REDIS_URL

# Append ssl_cert_reqs param if using rediss:// and not already set
if redis_url.startswith("rediss://") and "ssl_cert_reqs" not in redis_url:
    separator = "&" if "?" in redis_url else "?"
    redis_url = f"{redis_url}{separator}ssl_cert_reqs=CERT_NONE"

celery_app = Celery(
    "supportflow_tasks",
    broker=redis_url,
    backend=redis_url,
    include=["app.core.email"]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE} if settings.REDIS_URL.startswith("rediss://") else None,
    redis_backend_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE} if settings.REDIS_URL.startswith("rediss://") else None,
)
