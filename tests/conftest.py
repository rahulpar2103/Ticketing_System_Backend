"""
Shared test fixtures for the Ticketing System test suite.

Provides:
- Test database setup/teardown with per-test transaction rollback
- Fake user factories for each role
- Role-specific TestClient fixtures
- Redis auto-mocking (so tests never need a live Redis)
"""
import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.dependencies.db import get_db
from app.dependencies.user import get_current_user
from app.models.userModel import User, UserRole
from app.models.teamModel import Team
from app.models.ticketModel import Ticket, TicketStatus, Priority
from app.models.commentModel import Comment
from app.models import userModel, teamModel, ticketModel, commentModel
from app.db.database import Base
from app.core.security import hash_password

engine = create_engine(settings.TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ── Database lifecycle ──────────────────────────────────────────────────────

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


# ── Redis mock (applied to every test automatically) ────────────────────────

@pytest.fixture(autouse=True)
def _mock_redis():
    """Disable Redis for all tests — services fall back to DB queries."""
    with (
        patch("app.db.redis.safe_get", return_value=None),
        patch("app.db.redis.safe_setex"),
        patch("app.db.redis.safe_delete"),
        patch("app.db.redis.delete_by_prefix"),
    ):
        yield


# ── Fake user factories ─────────────────────────────────────────────────────

def make_fake_user(
    role: UserRole,
    user_id: int = 1,
    team_id: int | None = None,
    name: str = "Test User",
    username: str = "testuser",
    email: str = "test@example.com",
):
    user = User()
    user.id = user_id
    user.name = name
    user.username = username
    user.email = email
    user.role = role
    user.team_id = team_id
    user.is_active = True
    return user


def make_db_user(
    db,
    *,
    role: UserRole = UserRole.employee,
    name: str = "DB User",
    username: str = "dbuser",
    email: str = "db@example.com",
    password: str = "password123",
    team_id: int | None = None,
) -> User:
    """Insert a real user row and return the ORM object."""
    user = User(
        name=name,
        username=username,
        email=email,
        hashed_password=hash_password(password),
        role=role,
        team_id=team_id,
    )
    db.add(user)
    db.flush()          # assign .id without committing
    return user


def make_db_team(db, *, name: str = "Alpha Team", description: str = "Default team") -> Team:
    team = Team(name=name, description=description)
    db.add(team)
    db.flush()
    return team


def make_db_ticket(
    db,
    *,
    title: str = "Bug report",
    description: str = "Something broke",
    priority: Priority = Priority.medium,
    created_by: int,
    assigned_to: int | None = None,
    team_id: int | None = None,
    status: TicketStatus = TicketStatus.open,
) -> Ticket:
    ticket = Ticket(
        title=title,
        description=description,
        priority=priority,
        created_by=created_by,
        assigned_to=assigned_to,
        team_id=team_id,
        status=status,
    )
    db.add(ticket)
    db.flush()
    return ticket


def make_db_comment(
    db,
    *,
    comment: str = "A comment",
    ticket_id: int,
    user_id: int,
) -> Comment:
    c = Comment(comment=comment, ticket_id=ticket_id, user_id=user_id)
    db.add(c)
    db.flush()
    return c


# ── TestClient fixtures (one per role) ──────────────────────────────────────

def _seed_user_if_needed(db, role, username, email, user_id=None, team_id=None):
    """Insert a real DB user so FK constraints work. Returns the DB user."""
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        return existing
    user = User(
        name=f"Test {role.value}",
        username=username,
        email=email,
        hashed_password=hash_password("testpass123"),
        role=role,
        team_id=team_id,
    )
    db.add(user)
    db.flush()
    return user


def _make_client(db, fake_user):
    """Build a TestClient with overridden DB and auth dependencies."""
    def override_get_db():
        yield db

    def override_get_current_user():
        return fake_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture()
def client(db):
    """Default client — logged in as admin."""
    seeded = _seed_user_if_needed(db, UserRole.admin, "fixture_admin", "fixture_admin@test.com", user_id=None)
    db.flush()
    yield from _make_client(db, make_fake_user(UserRole.admin, user_id=seeded.id))


@pytest.fixture()
def admin_client(db):
    seeded = _seed_user_if_needed(db, UserRole.admin, "fixture_admin", "fixture_admin@test.com", user_id=None)
    db.flush()
    yield from _make_client(db, make_fake_user(UserRole.admin, user_id=seeded.id))


@pytest.fixture()
def agent_client(db):
    # Ensure a team exists for the agent
    team = db.query(Team).filter(Team.name == "fixture_team").first()
    if not team:
        team = Team(name="fixture_team", description="Fixture team")
        db.add(team)
        db.flush()
    seeded = _seed_user_if_needed(
        db, UserRole.agent, "fixture_agent", "fixture_agent@test.com",
        user_id=None, team_id=team.id,
    )
    db.flush()
    yield from _make_client(db, make_fake_user(UserRole.agent, user_id=seeded.id, team_id=team.id))


@pytest.fixture()
def employee_client(db):
    seeded = _seed_user_if_needed(
        db, UserRole.employee, "fixture_emp", "fixture_emp@test.com", user_id=None,
    )
    db.flush()
    yield from _make_client(db, make_fake_user(UserRole.employee, user_id=seeded.id))
