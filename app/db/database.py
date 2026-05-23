from sqlalchemy import NullPool
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.core.config import settings
from sqlalchemy.orm import declarative_base

Base=declarative_base()

engine = create_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,
    echo=settings.DEBUG
)
session_local=sessionmaker(autocommit=False,autoflush=False,bind=engine)


