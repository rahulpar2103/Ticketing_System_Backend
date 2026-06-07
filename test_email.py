from app.tasks.email_tasks import send_welcome_email_task

def test():
    print("Dispatching welcome email via Celery...")
    send_welcome_email_task.delay(
        email="rahul.pardasani03@gmail.com",
        username="testuser",
        password="Password@123",
    )
    print("Task dispatched. Check Celery worker logs.")

if __name__ == "__main__":
    test()
