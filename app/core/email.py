import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

def send_welcome_email(email: str, username: str, password: str):
    if not settings.SMTP_HOST:
        return "SMTP not configured"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Welcome to SupportFlow!"
    msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
    msg["To"] = email

    html_content = f"""
    <html>
        <body>
            <h2>Welcome to SupportFlow, {username}!</h2>
            <p>Your account has been successfully created.</p>
            <p><strong>Username:</strong> {username}</p>
            <p><strong>Password:</strong> {password}</p>
        </body>
    </html>
    """
    msg.attach(MIMEText(html_content, "html"))

    server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
    try:
        if settings.SMTP_TLS:
            server.starttls()
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(msg["From"], [email], msg.as_string())
    finally:
        server.quit()