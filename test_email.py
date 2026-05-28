from app.core.email import send_welcome_email

def test():
    print("Sending welcome email directly...")
    result = send_welcome_email(email="test@example.com", username="testuser", password="Password@123")
    print("Done. Result:", result)

if __name__ == "__main__":
    test()

