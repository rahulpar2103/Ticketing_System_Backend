"""
Integration tests for AuthService (create_user, login).

Uses the real test database with per-test transaction rollback.
"""
import pytest

from app.services.userServices.auth import auth_service
from app.schemas.userSchema import UserCreate
from app.models.userModel import UserRole, User
from app.core.exceptions import (
    AlreadyExistsException, PermissionDeniedException, NotFoundException,
)
from tests.conftest import make_fake_user, make_db_team


# ═══════════════════════════════════════════════════════════════════════════
# create_user
# ═══════════════════════════════════════════════════════════════════════════

class TestCreateUser:

    def _admin(self):
        return make_fake_user(UserRole.admin)

    def _user_data(self, **overrides):
        defaults = dict(
            name="Test User", username="testuser", email="test@example.com",
            password="StrongP@ss123!", role=UserRole.employee,
        )
        defaults.update(overrides)
        return UserCreate(**defaults)

    def test_create_user_persists_to_database(self, db):
        created = auth_service.create_user(self._admin(), self._user_data(), db)

        fetched = db.query(User).filter(User.email == "test@example.com").first()
        assert fetched is not None
        assert fetched.username == "testuser"
        assert fetched.hashed_password != "StrongP@ss123!"  # must be hashed

    def test_create_user_returns_user_response(self, db):
        result = auth_service.create_user(self._admin(), self._user_data(), db)
        assert result.username == "testuser"
        assert result.role == UserRole.employee

    def test_create_user_duplicate_email_raises(self, db):
        auth_service.create_user(self._admin(), self._user_data(), db)
        with pytest.raises(AlreadyExistsException):
            auth_service.create_user(self._admin(), self._user_data(), db)

    def test_create_user_duplicate_username_raises(self, db):
        auth_service.create_user(self._admin(), self._user_data(), db)
        with pytest.raises(AlreadyExistsException):
            auth_service.create_user(
                self._admin(),
                self._user_data(email="other@example.com"),
                db,
            )

    def test_create_user_invalid_username_with_at_sign(self, db):
        with pytest.raises(AlreadyExistsException, match="@"):
            auth_service.create_user(
                self._admin(),
                self._user_data(username="test@user"),
                db,
            )

    def test_create_user_invalid_username_with_dot(self, db):
        with pytest.raises(AlreadyExistsException, match=r"\."):
            auth_service.create_user(
                self._admin(),
                self._user_data(username="test.user"),
                db,
            )

    def test_non_admin_cannot_create_user(self, db):
        employee = make_fake_user(UserRole.employee)
        with pytest.raises(PermissionDeniedException):
            auth_service.create_user(employee, self._user_data(), db)

    def test_agent_cannot_create_user(self, db):
        agent = make_fake_user(UserRole.agent)
        with pytest.raises(PermissionDeniedException):
            auth_service.create_user(agent, self._user_data(), db)

    def test_create_user_with_valid_team_id(self, db):
        team = make_db_team(db, name="Eng")
        db.commit()
        data = self._user_data(team_id=team.id)
        result = auth_service.create_user(self._admin(), data, db)
        assert result.team_id == team.id

    def test_create_user_with_invalid_team_id(self, db):
        data = self._user_data(team_id=9999)
        with pytest.raises(NotFoundException, match="Team"):
            auth_service.create_user(self._admin(), data, db)

    def test_create_multiple_different_users(self, db):
        auth_service.create_user(self._admin(), self._user_data(), db)
        auth_service.create_user(
            self._admin(),
            self._user_data(username="second", email="second@example.com"),
            db,
        )
        assert db.query(User).count() == 2


# ═══════════════════════════════════════════════════════════════════════════
# login
# ═══════════════════════════════════════════════════════════════════════════

class TestLogin:

    class FakeForm:
        def __init__(self, username, password):
            self.username = username
            self.password = password

    def _seed_user(self, db):
        from app.core.security import hash_password
        user = User(
            name="Login User", username="loginuser", email="login@example.com",
            hashed_password=hash_password("StrongP@ss123!"),
            role=UserRole.employee,
        )
        db.add(user)
        db.commit()
        return user

    def test_login_with_username(self, db):
        self._seed_user(db)
        result = auth_service.login(self.FakeForm("loginuser", "StrongP@ss123!"), db)
        assert "access_token" in result
        assert result["token_type"] == "bearer"

    def test_login_with_email(self, db):
        self._seed_user(db)
        result = auth_service.login(self.FakeForm("login@example.com", "StrongP@ss123!"), db)
        assert "access_token" in result

    def test_login_wrong_password(self, db):
        from app.core.exceptions import InvalidCredentialsException
        self._seed_user(db)
        with pytest.raises(InvalidCredentialsException):
            auth_service.login(self.FakeForm("loginuser", "Wr0ngP@ss123!"), db)

    def test_login_nonexistent_user(self, db):
        from app.core.exceptions import InvalidCredentialsException
        with pytest.raises(InvalidCredentialsException):
            auth_service.login(self.FakeForm("nobody", "StrongP@ss123!"), db)

    def test_login_inactive_user(self, db):
        from app.core.exceptions import InvalidCredentialsException
        user = self._seed_user(db)
        user.is_active = False
        db.commit()
        with pytest.raises(InvalidCredentialsException, match="disabled"):
            auth_service.login(self.FakeForm("loginuser", "StrongP@ss123!"), db)
