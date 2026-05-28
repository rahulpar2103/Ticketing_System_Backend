from app.core.logger import logger

def send_welcome_email(email: str, username: str, password: str):
    logger.info("=" * 40)
    logger.info("WELCOME EMAIL STUB (Console/Logs)")
    logger.info(f"To      : {email}")
    logger.info(f"Username: {username}")
    logger.info(f"Password: ********")
    logger.info("=" * 40)