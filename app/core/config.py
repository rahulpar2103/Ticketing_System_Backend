from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    DATABASE_URL: str
    TEST_DATABASE_URL: str
    DB_POOL_SIZE: int
    DB_MAX_OVERFLOW: int
    DEBUG: bool
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REDIS_URL: str = "redis://localhost:6379"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = ""
    
    # AWS SES SMTP Configuration
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    MAIL_FROM: str = ""

    # Gemini LLM / RAG Configuration
    GEMINI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "models/gemini-embedding-2"
    LLM_MODEL: str = "gemini-2.5-flash"



    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://ticketing-system-frontend-lilac.vercel.app",
        "https://ticketing-system-frontend-8tzpolizj-anonymous21-03s-projects.vercel.app"
    ]
    
    model_config = SettingsConfigDict(env_file=(".env", "app/.env"))

settings = Settings()

# Expose GEMINI_API_KEY as GOOGLE_API_KEY for LangChain's langchain-google-genai
# which auto-reads GOOGLE_API_KEY from the environment.
if settings.GEMINI_API_KEY:
    os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY

