"""
Unit tests for all Pydantic schemas.

No database or network needed — pure validation logic.
"""
import pytest
from pydantic import ValidationError

from app.schemas.userSchema import (
    UserCreate, UserResponse, UserUpdate,
    PasswordUpdate, AdminPasswordReset, TokenResponse,
)
from app.schemas.ticketSchema import TicketCreate, TicketUpdate, TicketResponse
from app.schemas.commentSchema import CommentCreate, CommentUpdate, CommentResponse
from app.schemas.teamSchema import TeamCreate, TeamResponse, TeamUpdate
from app.models.userModel import UserRole
from app.models.ticketModel import TicketStatus, Priority


# ═══════════════════════════════════════════════════════════════════════════
# UserCreate
# ═══════════════════════════════════════════════════════════════════════════

class TestUserCreate:

    def test_valid_user_create(self):
        u = UserCreate(
            name="Alice", username="alice01", email="alice@example.com",
            password="StrongP@ss123!", role=UserRole.employee,
        )
        assert u.name == "Alice"
        assert u.role == UserRole.employee

    def test_name_stripped(self):
        u = UserCreate(
            name="  Bob  ", username="bob01", email="bob@example.com",
            password="StrongP@ss123!", role=UserRole.agent,
        )
        assert u.name == "Bob"

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError, match="empty"):
            UserCreate(
                name="   ", username="bob01", email="bob@example.com",
                password="StrongP@ss123!", role=UserRole.agent,
            )

    def test_empty_username_rejected(self):
        with pytest.raises(ValidationError, match="empty"):
            UserCreate(
                name="Bob", username="  ", email="bob@example.com",
                password="StrongP@ss123!", role=UserRole.agent,
            )

    def test_short_username_rejected(self):
        with pytest.raises(ValidationError, match="at least 3"):
            UserCreate(
                name="Bob", username="ab", email="bob@example.com",
                password="StrongP@ss123!", role=UserRole.agent,
            )

    def test_long_username_rejected(self):
        with pytest.raises(ValidationError, match="cannot exceed 50"):
            UserCreate(
                name="Bob", username="x" * 51, email="bob@example.com",
                password="StrongP@ss123!", role=UserRole.agent,
            )

    def test_long_name_rejected(self):
        with pytest.raises(ValidationError, match="cannot exceed 100"):
            UserCreate(
                name="x" * 101, username="bob01", email="bob@example.com",
                password="StrongP@ss123!", role=UserRole.agent,
            )

    def test_short_password_rejected(self):
        with pytest.raises(ValidationError, match="at least 8"):
            UserCreate(
                name="Bob", username="bob01", email="bob@example.com",
                password="Sh0rt!", role=UserRole.agent,
            )

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            UserCreate(
                name="Bob", username="bob01", email="not-an-email",
                password="StrongP@ss123!", role=UserRole.agent,
            )

    def test_invalid_role_rejected(self):
        with pytest.raises(ValidationError):
            UserCreate(
                name="Bob", username="bob01", email="bob@example.com",
                password="StrongP@ss123!", role="superadmin",
            )

    def test_team_id_optional(self):
        u = UserCreate(
            name="Bob", username="bob01", email="bob@example.com",
            password="StrongP@ss123!", role=UserRole.employee,
        )
        assert u.team_id is None

    def test_team_id_accepted(self):
        u = UserCreate(
            name="Bob", username="bob01", email="bob@example.com",
            password="StrongP@ss123!", role=UserRole.employee, team_id=5,
        )
        assert u.team_id == 5


# ═══════════════════════════════════════════════════════════════════════════
# UserUpdate
# ═══════════════════════════════════════════════════════════════════════════

class TestUserUpdate:

    def test_all_optional(self):
        u = UserUpdate()
        assert u.name is None
        assert u.username is None

    def test_partial_update(self):
        u = UserUpdate(name="NewName")
        assert u.name == "NewName"
        assert u.email is None

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError, match="empty"):
            UserUpdate(name="   ")

    def test_short_username_rejected(self):
        with pytest.raises(ValidationError, match="at least 3"):
            UserUpdate(username="ab")


# ═══════════════════════════════════════════════════════════════════════════
# PasswordUpdate / AdminPasswordReset
# ═══════════════════════════════════════════════════════════════════════════

class TestPasswordUpdate:

    def test_valid(self):
        p = PasswordUpdate(current_password="oldpass123", new_password="StrongNewP@ss123!")
        assert p.current_password == "oldpass123"

    def test_new_password_too_short(self):
        with pytest.raises(ValidationError, match="at least 8"):
            PasswordUpdate(current_password="oldpass123", new_password="Sh0rt!")

    def test_current_password_required(self):
        with pytest.raises(ValidationError):
            PasswordUpdate(new_password="StrongNewP@ss123!")


class TestAdminPasswordReset:

    def test_valid(self):
        p = AdminPasswordReset(new_password="StrongNewP@ss123!")
        assert p.new_password == "StrongNewP@ss123!"

    def test_new_password_too_short(self):
        with pytest.raises(ValidationError, match="at least 8"):
            AdminPasswordReset(new_password="Sh0rt!")

    def test_no_current_password_field(self):
        """Admin schema should NOT have a current_password field."""
        p = AdminPasswordReset(new_password="StrongNewP@ss123!")
        assert not hasattr(p, "current_password")


# ═══════════════════════════════════════════════════════════════════════════
# UserResponse
# ═══════════════════════════════════════════════════════════════════════════

class TestUserResponse:

    def test_from_attributes(self):
        class FakeUser:
            id = 1; name = "A"; username = "a"; email = "a@a.com"
            role = UserRole.admin; team_id = None; is_active = True
        resp = UserResponse.model_validate(FakeUser())
        assert resp.id == 1

    def test_password_not_exposed(self):
        data = dict(id=1, name="A", username="a", email="a@a.com",
                    role=UserRole.admin, team_id=None, is_active=True)
        resp = UserResponse(**data)
        dumped = resp.model_dump()
        assert "password" not in dumped
        assert "hashed_password" not in dumped


# ═══════════════════════════════════════════════════════════════════════════
# TicketCreate / TicketUpdate
# ═══════════════════════════════════════════════════════════════════════════

class TestTicketCreate:

    def test_valid(self):
        t = TicketCreate(title="Fix bug", description="It's broken", priority=Priority.high)
        assert t.priority == Priority.high

    def test_title_stripped(self):
        t = TicketCreate(title="  Fix bug  ", description="desc", priority=Priority.low)
        assert t.title == "Fix bug"

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError, match="empty"):
            TicketCreate(title="  ", description="desc", priority=Priority.low)

    def test_empty_description_rejected(self):
        with pytest.raises(ValidationError, match="empty"):
            TicketCreate(title="Fix", description="   ", priority=Priority.low)

    def test_title_too_long(self):
        with pytest.raises(ValidationError, match="150"):
            TicketCreate(title="x" * 151, description="desc", priority=Priority.low)

    def test_description_too_long(self):
        with pytest.raises(ValidationError, match="2000"):
            TicketCreate(title="Fix", description="x" * 2001, priority=Priority.low)

    def test_invalid_priority(self):
        with pytest.raises(ValidationError):
            TicketCreate(title="Fix", description="desc", priority="critical")


class TestTicketUpdate:

    def test_all_optional(self):
        t = TicketUpdate()
        assert t.title is None
        assert t.status is None

    def test_partial(self):
        t = TicketUpdate(status=TicketStatus.in_progress)
        assert t.status == TicketStatus.in_progress


# ═══════════════════════════════════════════════════════════════════════════
# CommentCreate / CommentUpdate
# ═══════════════════════════════════════════════════════════════════════════

class TestCommentCreate:

    def test_valid(self):
        c = CommentCreate(comment="Nice work!")
        assert c.comment == "Nice work!"

    def test_stripped(self):
        c = CommentCreate(comment="  Hello  ")
        assert c.comment == "Hello"

    def test_empty_rejected(self):
        with pytest.raises(ValidationError, match="empty"):
            CommentCreate(comment="   ")

    def test_too_long(self):
        with pytest.raises(ValidationError, match="2000"):
            CommentCreate(comment="x" * 2001)


class TestCommentUpdate:

    def test_valid(self):
        c = CommentUpdate(comment="Updated")
        assert c.comment == "Updated"

    def test_empty_rejected(self):
        with pytest.raises(ValidationError, match="empty"):
            CommentUpdate(comment="   ")


# ═══════════════════════════════════════════════════════════════════════════
# TeamCreate / TeamUpdate
# ═══════════════════════════════════════════════════════════════════════════

class TestTeamCreate:

    def test_valid(self):
        t = TeamCreate(name="Ops", description="Operations team")
        assert t.name == "Ops"


class TestTeamUpdate:

    def test_all_optional(self):
        t = TeamUpdate()
        assert t.name is None
        assert t.description is None


# ═══════════════════════════════════════════════════════════════════════════
# TokenResponse
# ═══════════════════════════════════════════════════════════════════════════

class TestTokenResponse:

    def test_valid(self):
        t = TokenResponse(access_token="abc123", token_type="bearer")
        assert t.token_type == "bearer"
