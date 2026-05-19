"""
HTTP tests for Team routes (/teams/*).
"""
import pytest
from tests.conftest import make_db_user, make_db_team
from app.models.userModel import UserRole


class TestCreateTeam:
    def test_admin_creates_team(self, admin_client):
        resp = admin_client.post("/teams", json={
            "name": "Ops", "description": "Operations"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "Ops"

    def test_employee_cannot_create(self, employee_client):
        resp = employee_client.post("/teams", json={
            "name": "Ops", "description": "Operations"})
        assert resp.status_code == 403


class TestGetAllTeams:
    def test_admin_lists_teams(self, admin_client, db):
        make_db_team(db, name="T1")
        make_db_team(db, name="T2")
        db.commit()
        resp = admin_client.get("/teams")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_agent_cannot_list_all(self, agent_client):
        resp = agent_client.get("/teams")
        assert resp.status_code == 403


class TestGetTeam:
    def test_admin_gets_team(self, admin_client, db):
        team = make_db_team(db, name="Alpha")
        db.commit()
        resp = admin_client.get(f"/teams/{team.id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Alpha"

    def test_nonexistent_team_404(self, admin_client):
        resp = admin_client.get("/teams/9999")
        assert resp.status_code == 404


class TestUpdateTeam:
    def test_admin_updates_team(self, admin_client, db):
        team = make_db_team(db)
        db.commit()
        resp = admin_client.put(f"/teams/{team.id}", json={"name": "Beta"})
        assert resp.status_code == 200
        assert "updated" in resp.json()["message"]


class TestDeleteTeam:
    def test_admin_deletes_team(self, admin_client, db):
        team = make_db_team(db)
        db.commit()
        resp = admin_client.delete(f"/teams/{team.id}")
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"]


class TestGetTeamMembers:
    def test_admin_gets_members(self, admin_client, db):
        team = make_db_team(db)
        make_db_user(db, username="m1", email="m1@t.com", team_id=team.id)
        db.commit()
        resp = admin_client.get(f"/teams/{team.id}/members")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) >= 1


class TestReactivateTeam:
    def test_admin_reactivates_team(self, admin_client, db):
        team = make_db_team(db, name="Inactive")
        team.is_active = False
        db.commit()
        resp = admin_client.patch(f"/teams/{team.id}/reactivate")
        assert resp.status_code == 200
        assert "reactivated" in resp.json()["message"]


class TestTeamStats:
    def test_admin_gets_team_stats(self, admin_client, db):
        team = make_db_team(db, name="Stats")
        db.commit()
        resp = admin_client.get(f"/teams/{team.id}/stats")
        assert resp.status_code == 200
        assert resp.json()["team_id"] == team.id
        assert "total_tickets" in resp.json()
