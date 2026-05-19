"""
Integration tests for User services (admin, agent, employee).

Covers: get_user, get_all_users, update_user, delete_user, update_user_password.
"""
import pytest

from app.services.userServices.admin import user_service_admin
from app.services.userServices.agent import user_service_agent
from app.services.userServices.employee import user_service_employee
from app.models.userModel import UserRole
from app.schemas.userSchema import UserUpdate, PasswordUpdate, AdminPasswordReset
from app.core.exceptions import (
    PermissionDeniedException, NotFoundException, AlreadyExistsException,
    InvalidCredentialsException,
)
from app.core.security import verify_password
from tests.conftest import make_fake_user, make_db_user, make_db_team


# ═══════════════════════════════════════════════════════════════════════════
# Admin User Service
# ═══════════════════════════════════════════════════════════════════════════

class TestAdminGetAllUsers:

    def test_admin_can_list_users(self, db):
        make_db_user(db, username="u1", email="u1@test.com")
        make_db_user(db, username="u2", email="u2@test.com")
        db.commit()
        admin = make_fake_user(UserRole.admin)
        result = user_service_admin.get_all_users(admin, db, limit=10, offset=0)
        assert len(result["items"]) >= 2

    def test_non_admin_cannot_list_users(self, db):
        agent = make_fake_user(UserRole.agent, user_id=2)
        with pytest.raises(PermissionDeniedException):
            user_service_admin.get_all_users(agent, db, limit=10, offset=0)

    def test_pagination(self, db):
        for i in range(5):
            make_db_user(db, username=f"pg{i}", email=f"pg{i}@test.com")
        db.commit()
        admin = make_fake_user(UserRole.admin)
        page1 = user_service_admin.get_all_users(admin, db, limit=2, offset=0)
        page2 = user_service_admin.get_all_users(admin, db, limit=2, offset=2)
        assert len(page1["items"]) == 2
        assert len(page2["items"]) == 2


class TestAdminGetUser:

    def test_admin_can_get_user(self, db):
        user = make_db_user(db)
        db.commit()
        admin = make_fake_user(UserRole.admin)
        result = user_service_admin.get_user(admin, user.id, db)
        assert result.username == "dbuser"

    def test_admin_get_nonexistent_user(self, db):
        admin = make_fake_user(UserRole.admin)
        with pytest.raises(NotFoundException):
            user_service_admin.get_user(admin, 9999, db)

    def test_non_admin_cannot_get_via_admin_service(self, db):
        employee = make_fake_user(UserRole.employee)
        with pytest.raises(PermissionDeniedException):
            user_service_admin.get_user(employee, 1, db)


class TestAdminUpdateUser:

    def test_admin_update_name(self, db):
        user = make_db_user(db)
        db.commit()
        admin = make_fake_user(UserRole.admin)
        result = user_service_admin.update_user(
            admin, user.id, UserUpdate(name="NewName"), db,
        )
        assert "updated" in result["message"]

    def test_admin_update_duplicate_username(self, db):
        make_db_user(db, username="first", email="first@test.com")
        u2 = make_db_user(db, username="second", email="second@test.com")
        db.commit()
        admin = make_fake_user(UserRole.admin)
        with pytest.raises(AlreadyExistsException, match="Username"):
            user_service_admin.update_user(
                admin, u2.id, UserUpdate(username="first"), db,
            )

    def test_admin_update_duplicate_email(self, db):
        make_db_user(db, username="first", email="first@test.com")
        u2 = make_db_user(db, username="second", email="second@test.com")
        db.commit()
        admin = make_fake_user(UserRole.admin)
        with pytest.raises(AlreadyExistsException, match="Email"):
            user_service_admin.update_user(
                admin, u2.id, UserUpdate(email="first@test.com"), db,
            )

    def test_admin_update_nonexistent_user(self, db):
        admin = make_fake_user(UserRole.admin)
        with pytest.raises(NotFoundException):
            user_service_admin.update_user(admin, 9999, UserUpdate(name="X"), db)

    def test_non_admin_cannot_update(self, db):
        with pytest.raises(PermissionDeniedException):
            user_service_admin.update_user(
                make_fake_user(UserRole.employee), 1, UserUpdate(name="X"), db,
            )


class TestAdminDeleteUser:

    def test_admin_soft_deletes_user(self, db):
        user = make_db_user(db)
        db.commit()
        admin = make_fake_user(UserRole.admin)
        result = user_service_admin.delete_user(admin, user.id, db)
        assert "deleted" in result["message"]
        db.refresh(user)
        assert user.is_active is False

    def test_admin_cannot_delete_self(self, db):
        admin = make_fake_user(UserRole.admin, user_id=1)
        make_db_user(db, username="admin", email="admin@test.com", role=UserRole.admin)
        db.commit()
        with pytest.raises(PermissionDeniedException, match="yourself"):
            user_service_admin.delete_user(admin, 1, db)

    def test_admin_delete_nonexistent_user(self, db):
        admin = make_fake_user(UserRole.admin)
        with pytest.raises(NotFoundException):
            user_service_admin.delete_user(admin, 9999, db)


class TestAdminPasswordReset:

    def test_admin_can_reset_password(self, db):
        user = make_db_user(db, password="OldStrongP@ss1!")
        db.commit()
        admin = make_fake_user(UserRole.admin)
        result = user_service_admin.update_user_password(
            admin, user.id, AdminPasswordReset(new_password="StrongP@ss1234!"), db,
        )
        assert "updated" in result["message"]
        db.refresh(user)
        assert verify_password("StrongP@ss1234!", user.hashed_password)

    def test_non_admin_cannot_admin_reset(self, db):
        with pytest.raises(PermissionDeniedException):
            user_service_admin.update_user_password(
                make_fake_user(UserRole.agent),
                1,
                AdminPasswordReset(new_password="StrongP@ss1234!"),
                db,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Employee User Service
# ═══════════════════════════════════════════════════════════════════════════

class TestEmployeeGetUser:

    def test_employee_can_view_own_profile(self, db):
        user = make_db_user(db, role=UserRole.employee)
        db.commit()
        fake_emp = make_fake_user(UserRole.employee, user_id=user.id)
        result = user_service_employee.get_user(fake_emp, user.id, db)
        assert result.username == "dbuser"

    def test_employee_cannot_view_other_profile(self, db):
        user = make_db_user(db, role=UserRole.employee)
        db.commit()
        fake_emp = make_fake_user(UserRole.employee, user_id=9999)
        with pytest.raises(PermissionDeniedException):
            user_service_employee.get_user(fake_emp, user.id, db)


class TestEmployeePasswordUpdate:

    def test_employee_can_change_own_password(self, db):
        user = make_db_user(db, role=UserRole.employee, password="oldpass123")
        db.commit()
        fake_emp = make_fake_user(UserRole.employee, user_id=user.id)
        result = user_service_employee.update_user_password(
            fake_emp, user.id,
            PasswordUpdate(current_password="oldpass123", new_password="StrongP@ss1234!"),
            db,
        )
        assert "updated" in result["message"]
        db.refresh(user)
        assert verify_password("StrongP@ss1234!", user.hashed_password)

    def test_employee_wrong_current_password(self, db):
        user = make_db_user(db, role=UserRole.employee, password="oldpass123")
        db.commit()
        fake_emp = make_fake_user(UserRole.employee, user_id=user.id)
        with pytest.raises(InvalidCredentialsException):
            user_service_employee.update_user_password(
                fake_emp, user.id,
                PasswordUpdate(current_password="wrongpass1", new_password="StrongP@ss1234!"),
                db,
            )

    def test_employee_cannot_change_others_password(self, db):
        user = make_db_user(db, role=UserRole.employee, password="oldpass123")
        db.commit()
        fake_emp = make_fake_user(UserRole.employee, user_id=9999)
        with pytest.raises(PermissionDeniedException):
            user_service_employee.update_user_password(
                fake_emp, user.id,
                PasswordUpdate(current_password="oldpass123", new_password="StrongP@ss1234!"),
                db,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Agent User Service
# ═══════════════════════════════════════════════════════════════════════════

class TestAgentGetUser:

    def test_agent_can_view_own_profile(self, db):
        team = make_db_team(db)
        user = make_db_user(db, role=UserRole.agent, username="agent1", email="agent1@test.com", team_id=team.id)
        db.commit()
        fake_agent = make_fake_user(UserRole.agent, user_id=user.id, team_id=team.id)
        result = user_service_agent.get_user(fake_agent, user.id, db)
        assert result.username == "agent1"

    def test_agent_can_view_teammate(self, db):
        team = make_db_team(db)
        agent = make_db_user(db, role=UserRole.agent, username="agent1", email="a1@test.com", team_id=team.id)
        teammate = make_db_user(db, role=UserRole.agent, username="agent2", email="a2@test.com", team_id=team.id)
        db.commit()
        fake_agent = make_fake_user(UserRole.agent, user_id=agent.id, team_id=team.id)
        result = user_service_agent.get_user(fake_agent, teammate.id, db)
        assert result.username == "agent2"

    def test_agent_cannot_view_user_on_different_team(self, db):
        team1 = make_db_team(db, name="Team1")
        team2 = make_db_team(db, name="Team2")
        agent = make_db_user(db, role=UserRole.agent, username="agent1", email="a1@test.com", team_id=team1.id)
        other = make_db_user(db, role=UserRole.agent, username="agent2", email="a2@test.com", team_id=team2.id)
        db.commit()
        fake_agent = make_fake_user(UserRole.agent, user_id=agent.id, team_id=team1.id)
        with pytest.raises(PermissionDeniedException):
            user_service_agent.get_user(fake_agent, other.id, db)


class TestAgentPasswordUpdate:

    def test_agent_can_change_own_password(self, db):
        user = make_db_user(db, role=UserRole.agent, password="oldpass123")
        db.commit()
        fake_agent = make_fake_user(UserRole.agent, user_id=user.id)
        result = user_service_agent.update_user_password(
            fake_agent, user.id,
            PasswordUpdate(current_password="oldpass123", new_password="StrongP@ss1234!"),
            db,
        )
        assert "updated" in result["message"]

    def test_agent_cannot_change_others_password(self, db):
        user = make_db_user(db, role=UserRole.agent, password="oldpass123")
        db.commit()
        fake_agent = make_fake_user(UserRole.agent, user_id=9999)
        with pytest.raises(PermissionDeniedException):
            user_service_agent.update_user_password(
                fake_agent, user.id,
                PasswordUpdate(current_password="oldpass123", new_password="StrongP@ss1234!"),
                db,
            )
