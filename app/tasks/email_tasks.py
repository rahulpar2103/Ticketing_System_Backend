from app.core.celery_app import celery_app
from app.core.email import send_email, build_welcome_html
from app.core.logger import logger


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def send_welcome_email_task(self, email: str, username: str, password: str):
    try:
        html = build_welcome_html(username, password)
        send_email(to=email, subject="Welcome to SupportFlow!", html_body=html)
    except Exception as exc:
        logger.error(f"Email task failed for {email}: {exc}")
        raise self.retry(exc=exc)
