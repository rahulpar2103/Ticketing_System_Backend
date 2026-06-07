import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.core.config import settings
from app.core.logger import logger


def send_email(to: str, subject: str, html_body: str):
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        logger.warning(f"SMTP not configured, skipping email to {to}")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.MAIL_FROM
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.MAIL_FROM, to, msg.as_string())

    logger.info(f"Email sent to {to}")


def build_welcome_html(username: str, password: str) -> str:
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2>Welcome to SupportFlow, {username}!</h2>
            <p>Your account has been created.</p>
            <div style="background: #f3f4f6; padding: 15px; border-radius: 6px; margin: 16px 0;">
                <p style="margin: 4px 0;"><strong>Username:</strong> {username}</p>
                <p style="margin: 4px 0;"><strong>Password:</strong> {password}</p>
            </div>
            <p>Please log in and change your password.</p>
        </div>
    </body>
    </html>
    """