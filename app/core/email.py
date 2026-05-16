# app/core/email.py
async def send_welcome_email(email: str, username: str, password: str):
    print("=" * 40)
    print("WELCOME EMAIL")
    print(f"To      : {email}")
    print(f"Username: {username}")
    print(f"Password: {password}")
    print("=" * 40)