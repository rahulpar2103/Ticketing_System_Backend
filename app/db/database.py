# pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine
from app.core.config import settings
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import declarative_base

Base=declarative_base()

engine=create_engine(
    settings.DATABASE_URL, 
    pool_size=settings.DB_POOL_SIZE, 
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DEBUG
    )
session_local=sessionmaker(autocommit=False,autoflush=False,bind=engine)


