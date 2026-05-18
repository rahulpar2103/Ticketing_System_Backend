# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient
from app.main import app
# pyrefly: ignore [missing-import]
from app.dependencies.db import get_db
# pyrefly: ignore [missing-import]
from app.dependencies.user import get_current_user
from app.models.userModel import User, UserRole
from app.models import userModel, teamModel, ticketModel, commentModel
# pyrefly: ignore [missing-import]
from app.db.database import Base

engine = create_engine(settings.TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

def make_fake_user(role: UserRole, user_id: int = 1, team_id: int = None):
    user = User()
    user.id = user_id
    user.username = "testuser"
    user.email = "test@example.com"
    user.role = role
    user.team_id = team_id
    user.is_active = True
    return user

@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    def override_get_current_user():
        return make_fake_user(UserRole.admin)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
