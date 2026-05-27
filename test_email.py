import time
from app.core.email import send_welcome_email

def test():
    result = send_welcome_email.delay(email="test@example.com", username="testuser", password="Password@123")
    print("Task ID:", result.id)
    # Wait a short while for the worker to process
    time.sleep(5)
    if result.ready():
        print("Result:", result.result)
    else:
        print("Task still processing or pending")

if __name__ == "__main__":
    test()
