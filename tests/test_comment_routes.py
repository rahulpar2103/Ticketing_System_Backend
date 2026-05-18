"""
HTTP tests for Comment routes (/tickets/{id}/comments, /comments/{id}).
"""
import pytest
from tests.conftest import make_db_user, make_db_team, make_db_ticket, make_db_comment
from app.models.userModel import UserRole


class TestCreateComment:
    def test_admin_creates_comment(self, admin_client, db):
        admin = make_db_user(db, role=UserRole.admin, username="adm", email="adm@t.com")
        ticket = make_db_ticket(db, created_by=admin.id)
        db.commit()
        resp = admin_client.post(
            f"/tickets/{ticket.id}/comments", json={"comment": "Nice"})
        assert resp.status_code == 201
        assert resp.json()["comment"] == "Nice"

    def test_empty_comment_rejected(self, admin_client, db):
        admin = make_db_user(db, role=UserRole.admin, username="adm", email="adm@t.com")
        ticket = make_db_ticket(db, created_by=admin.id)
        db.commit()
        resp = admin_client.post(
            f"/tickets/{ticket.id}/comments", json={"comment": "  "})
        assert resp.status_code == 422

    def test_comment_on_nonexistent_ticket(self, admin_client):
        resp = admin_client.post(
            "/tickets/9999/comments", json={"comment": "Hello"})
        assert resp.status_code == 404


class TestGetTicketComments:
    def test_admin_gets_comments(self, admin_client, db):
        admin = make_db_user(db, role=UserRole.admin, username="adm", email="adm@t.com")
        ticket = make_db_ticket(db, created_by=admin.id)
        make_db_comment(db, ticket_id=ticket.id, user_id=admin.id, comment="C1")
        db.commit()
        resp = admin_client.get(f"/tickets/{ticket.id}/comments")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestGetSingleComment:
    def test_admin_gets_comment(self, admin_client, db):
        admin = make_db_user(db, role=UserRole.admin, username="adm", email="adm@t.com")
        ticket = make_db_ticket(db, created_by=admin.id)
        comment = make_db_comment(db, ticket_id=ticket.id, user_id=admin.id)
        db.commit()
        resp = admin_client.get(f"/comments/{comment.id}")
        assert resp.status_code == 200

    def test_nonexistent_comment_404(self, admin_client):
        resp = admin_client.get("/comments/9999")
        assert resp.status_code == 404


class TestUpdateComment:
    def test_admin_updates_comment(self, admin_client, db):
        admin = make_db_user(db, role=UserRole.admin, username="adm", email="adm@t.com")
        ticket = make_db_ticket(db, created_by=admin.id)
        comment = make_db_comment(db, ticket_id=ticket.id, user_id=admin.id)
        db.commit()
        resp = admin_client.patch(
            f"/comments/{comment.id}", json={"comment": "Edited"})
        assert resp.status_code == 200
        assert resp.json()["comment"] == "Edited"
        assert resp.json()["is_edited"] is True


class TestDeleteComment:
    def test_admin_deletes_comment(self, admin_client, db):
        admin = make_db_user(db, role=UserRole.admin, username="adm", email="adm@t.com")
        ticket = make_db_ticket(db, created_by=admin.id)
        comment = make_db_comment(db, ticket_id=ticket.id, user_id=admin.id)
        db.commit()
        resp = admin_client.delete(f"/comments/{comment.id}")
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"]

    def test_employee_cannot_delete(self, employee_client, db):
        admin = make_db_user(db, role=UserRole.admin, username="adm", email="adm@t.com")
        ticket = make_db_ticket(db, created_by=admin.id)
        comment = make_db_comment(db, ticket_id=ticket.id, user_id=admin.id)
        db.commit()
        resp = employee_client.delete(f"/comments/{comment.id}")
        assert resp.status_code == 403
