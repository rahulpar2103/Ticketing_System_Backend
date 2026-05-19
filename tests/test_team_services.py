"""
Integration tests for Team services (admin, agent, employee).
"""
import pytest

from app.services.teamService.admin import team_service_admin
from app.services.teamService.agent import team_service_agent
from app.services.teamService.employee import team_service_employee
from app.schemas.teamSchema import TeamCreate, TeamUpdate
from app.models.userModel import UserRole
from app.core.exceptions import (
    PermissionDeniedException, NotFoundException, AlreadyExistsException,
)
from tests.conftest import make_fake_user, make_db_team, make_db_user


# ═══════════════════════════════════════════════════════════════════════════
# Admin Team Service
# ═══════════════════════════════════════════════════════════════════════════

class TestAdminCreateTeam:

    def test_admin_creates_team(self, db):
        admin = make_fake_user(UserRole.admin)
        result = team_service_admin.create_team(
            TeamCreate(name="Ops", description="Operations"), admin, db,
        )
        assert result.name == "Ops"

    def test_duplicate_team_name_rejected(self, db):
        admin = make_fake_user(UserRole.admin)
        team_service_admin.create_team(
            TeamCreate(name="Ops", description="First"), admin, db,
        )
        with pytest.raises(AlreadyExistsException):
            team_service_admin.create_team(
                TeamCreate(name="Ops", description="Second"), admin, db,
            )

    def test_non_admin_cannot_create_team(self, db):
        agent = make_fake_user(UserRole.agent)
        with pytest.raises(PermissionDeniedException):
            team_service_admin.create_team(
                TeamCreate(name="Ops", description="X"), agent, db,
            )


class TestAdminGetTeams:

    def test_admin_lists_teams(self, db):
        make_db_team(db, name="T1")
        make_db_team(db, name="T2")
        db.commit()
        admin = make_fake_user(UserRole.admin)
        result = team_service_admin.get_all_teams(admin, db, 10, 0)
        assert len(result["items"]) >= 2

    def test_admin_get_single_team(self, db):
        team = make_db_team(db, name="Alpha")
        db.commit()
        admin = make_fake_user(UserRole.admin)
        result = team_service_admin.get_team(team.id, admin, db)
        assert result.name == "Alpha"

    def test_admin_get_nonexistent_team(self, db):
        admin = make_fake_user(UserRole.admin)
        with pytest.raises(NotFoundException):
            team_service_admin.get_team(9999, admin, db)


class TestAdminUpdateTeam:

    def test_admin_updates_team(self, db):
        team = make_db_team(db, name="Old")
        db.commit()
        admin = make_fake_user(UserRole.admin)
        result = team_service_admin.update_team(
            team.id, TeamUpdate(name="New"), admin, db,
        )
        assert "updated" in result["message"]

    def test_admin_update_duplicate_name(self, db):
        make_db_team(db, name="Taken")
        team = make_db_team(db, name="Free")
        db.commit()
        admin = make_fake_user(UserRole.admin)
        with pytest.raises(AlreadyExistsException):
            team_service_admin.update_team(
                team.id, TeamUpdate(name="Taken"), admin, db,
            )


class TestAdminDeleteTeam:

    def test_admin_soft_deletes_team(self, db):
        team = make_db_team(db)
        db.commit()
        admin = make_fake_user(UserRole.admin)
        result = team_service_admin.delete_team(team.id, admin, db)
        assert "deleted" in result["message"]
        db.refresh(team)
        assert team.is_active is False

    def test_admin_delete_nonexistent_team(self, db):
        admin = make_fake_user(UserRole.admin)
        with pytest.raises(NotFoundException):
            team_service_admin.delete_team(9999, admin, db)


class TestAdminGetTeamMembers:

    def test_admin_gets_team_members(self, db):
        team = make_db_team(db)
        make_db_user(db, username="m1", email="m1@t.com", team_id=team.id)
        make_db_user(db, username="m2", email="m2@t.com", team_id=team.id)
        db.commit()
        admin = make_fake_user(UserRole.admin)
        result = team_service_admin.get_team_members(team.id, admin, db, 10, 0)
        assert len(result["items"]) == 2


# ═══════════════════════════════════════════════════════════════════════════
# Agent Team Service
# ═══════════════════════════════════════════════════════════════════════════

class TestAgentGetTeam:

    def test_agent_can_view_own_team(self, db):
        team = make_db_team(db)
        db.commit()
        agent = make_fake_user(UserRole.agent, user_id=2, team_id=team.id)
        result = team_service_agent.get_team(team.id, agent, db)
        assert result.name == "Alpha Team"

    def test_agent_cannot_view_other_team(self, db):
        team1 = make_db_team(db, name="T1")
        team2 = make_db_team(db, name="T2")
        db.commit()
        agent = make_fake_user(UserRole.agent, user_id=2, team_id=team1.id)
        with pytest.raises(PermissionDeniedException):
            team_service_agent.get_team(team2.id, agent, db)


class TestAgentGetTeamMembers:

    def test_agent_can_list_own_team_members(self, db):
        team = make_db_team(db)
        make_db_user(db, username="m1", email="m1@t.com", team_id=team.id)
        db.commit()
        agent = make_fake_user(UserRole.agent, user_id=2, team_id=team.id)
        result = team_service_agent.get_team_members(team.id, agent, db, 10, 0)
        assert len(result["items"]) >= 1

    def test_agent_cannot_list_other_team_members(self, db):
        team1 = make_db_team(db, name="T1")
        team2 = make_db_team(db, name="T2")
        db.commit()
        agent = make_fake_user(UserRole.agent, user_id=2, team_id=team1.id)
        with pytest.raises(PermissionDeniedException):
            team_service_agent.get_team_members(team2.id, agent, db, 10, 0)


# ═══════════════════════════════════════════════════════════════════════════
# Employee Team Service
# ═══════════════════════════════════════════════════════════════════════════

class TestEmployeeGetTeam:

    def test_employee_can_view_own_team(self, db):
        team = make_db_team(db)
        db.commit()
        emp = make_fake_user(UserRole.employee, user_id=3, team_id=team.id)
        result = team_service_employee.get_team(team.id, emp, db)
        assert result.name == "Alpha Team"

    def test_employee_without_team_rejected(self, db):
        emp = make_fake_user(UserRole.employee, user_id=3, team_id=None)
        with pytest.raises(PermissionDeniedException, match="not assigned"):
            team_service_employee.get_team(1, emp, db)

    def test_employee_cannot_view_other_team(self, db):
        team1 = make_db_team(db, name="T1")
        team2 = make_db_team(db, name="T2")
        db.commit()
        emp = make_fake_user(UserRole.employee, user_id=3, team_id=team1.id)
        with pytest.raises(PermissionDeniedException):
            team_service_employee.get_team(team2.id, emp, db)
