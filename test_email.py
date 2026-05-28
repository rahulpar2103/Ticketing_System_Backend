from app.core.email import send_welcome_email

def test():
    print("Testing local email logging...")
    send_welcome_email(email="test@example.com", username="testuser", password="Password@123")

if __name__ == "__main__":
    test()


