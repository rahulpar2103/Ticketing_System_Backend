from app.core.celery_app import celery_app

@celery_app.task
def send_welcome_email(email: str, username: str, password: str):
    print("=" * 40)
    print("WELCOME EMAIL (via Celery)")
    print(f"To      : {email}")
    print(f"Username: {username}")
    print(f"Password: ********")
    print("=" * 40)