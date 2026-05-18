"""
HTTP tests for Ticket routes (/tickets/*).
"""
import pytest
from tests.conftest import make_db_user, make_db_team, make_db_ticket
from app.models.userModel import UserRole
from app.models.ticketModel import TicketStatus


class TestCreateTicketRoute:
    def test_admin_creates_ticket(self, admin_client, db):
        resp = admin_client.post("/tickets", json={
            "title": "Bug", "description": "Broken", "priority": "high",
        })
        assert resp.status_code == 201
        assert resp.json()["title"] == "Bug"

    def test_invalid_priority_rejected(self, admin_client):
        resp = admin_client.post("/tickets", json={
            "title": "X", "description": "Y", "priority": "critical",
        })
        assert resp.status_code == 422

    def test_empty_title_rejected(self, admin_client):
        resp = admin_client.post("/tickets", json={
            "title": "  ", "description": "Y", "priority": "low",
        })
        assert resp.status_code == 422


class TestGetTicketsRoute:
    def test_admin_gets_all_tickets(self, admin_client, db):
        admin = make_db_user(db, role=UserRole.admin, username="adm", email="adm@t.com")
        make_db_ticket(db, created_by=admin.id)
        db.commit()
        resp = admin_client.get("/tickets")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestGetSingleTicketRoute:
    def test_admin_gets_ticket(self, admin_client, db):
        admin = make_db_user(db, role=UserRole.admin, username="adm", email="adm@t.com")
        ticket = make_db_ticket(db, created_by=admin.id, title="Find me")
        db.commit()
        resp = admin_client.get(f"/tickets/{ticket.id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Find me"

    def test_nonexistent_ticket_404(self, admin_client):
        resp = admin_client.get("/tickets/9999")
        assert resp.status_code == 404


class TestUpdateTicketRoute:
    def test_admin_updates_ticket(self, admin_client, db):
        admin = make_db_user(db, role=UserRole.admin, username="adm", email="adm@t.com")
        ticket = make_db_ticket(db, created_by=admin.id)
        db.commit()
        resp = admin_client.patch(f"/tickets/{ticket.id}", json={"title": "New Title"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    def test_update_nonexistent_ticket(self, admin_client):
        resp = admin_client.patch("/tickets/9999", json={"title": "X"})
        assert resp.status_code == 404


class TestGetCreatedTickets:
    def test_admin_gets_own_created(self, admin_client, db):
        admin = make_db_user(db, role=UserRole.admin, username="adm", email="adm@t.com")
        make_db_ticket(db, created_by=admin.id)
        db.commit()
        resp = admin_client.get("/tickets/created-by-me")
        assert resp.status_code == 200


class TestGetAssignedTickets:
    def test_admin_gets_assigned(self, admin_client, db):
        admin = make_db_user(db, role=UserRole.admin, username="adm", email="adm@t.com")
        make_db_ticket(db, created_by=admin.id, assigned_to=admin.id)
        db.commit()
        resp = admin_client.get("/tickets/assigned-to-me")
        assert resp.status_code == 200


class TestTeamTicketsRoute:
    def test_employee_gets_403(self, employee_client, db):
        team = make_db_team(db)
        db.commit()
        resp = employee_client.get(f"/tickets/team/{team.id}")
        assert resp.status_code == 403
