"""
HTTP tests for User routes (/users/*).
Tests the full request→response cycle through FastAPI's TestClient.
"""
import pytest
from tests.conftest import make_fake_user, make_db_user, make_db_team
from app.dependencies.user import get_current_user
from app.main import app
from app.models.userModel import UserRole


class TestGetAllUsers:
    def test_admin_gets_users(self, admin_client, db):
        make_db_user(db, username="u1", email="u1@t.com")
        db.commit()
        resp = admin_client.get("/users")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_agent_gets_403(self, agent_client):
        resp = agent_client.get("/users")
        assert resp.status_code == 403


class TestGetUser:
    def test_admin_gets_user_by_id(self, admin_client, db):
        user = make_db_user(db, username="target", email="target@t.com")
        db.commit()
        resp = admin_client.get(f"/users/{user.id}")
        assert resp.status_code == 200
        assert resp.json()["username"] == "target"

    def test_admin_gets_404_for_missing(self, admin_client):
        resp = admin_client.get("/users/9999")
        assert resp.status_code == 404


class TestUpdateUser:
    def test_admin_updates_user(self, admin_client, db):
        user = make_db_user(db, username="upd", email="upd@t.com")
        db.commit()
        resp = admin_client.patch(f"/users/{user.id}", json={"name": "NewName"})
        assert resp.status_code == 200
        assert "updated" in resp.json()["message"]

    def test_employee_cannot_update(self, employee_client, db):
        user = make_db_user(db, username="upd", email="upd@t.com")
        db.commit()
        resp = employee_client.patch(f"/users/{user.id}", json={"name": "X"})
        assert resp.status_code == 403


class TestDeleteUser:
    def test_admin_deletes_user(self, admin_client, db):
        user = make_db_user(db, username="del", email="del@t.com")
        db.commit()
        resp = admin_client.delete(f"/users/{user.id}")
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"]

    def test_admin_cannot_delete_self(self, admin_client, db):
        # Find the seeded admin's actual ID
        from app.models.userModel import User
        admin = db.query(User).filter(User.username == "fixture_admin").first()
        resp = admin_client.delete(f"/users/{admin.id}")
        assert resp.status_code == 403


class TestPasswordUpdate:
    def test_employee_changes_own_password(self, db):
        user = make_db_user(db, role=UserRole.employee, password="oldpass123")
        db.commit()
        # Override to be this specific employee
        fake = make_fake_user(UserRole.employee, user_id=user.id)
        app.dependency_overrides[get_current_user] = lambda: fake
        from tests.conftest import _make_client
        from app.dependencies.db import get_db
        def override_db():
            yield db
        app.dependency_overrides[get_db] = override_db
        from fastapi.testclient import TestClient
        with TestClient(app, raise_server_exceptions=False) as c:
            resp = c.patch(
                f"/users/{user.id}/password",
                json={"current_password": "oldpass123", "new_password": "newpass1234"},
            )
        app.dependency_overrides.clear()
        assert resp.status_code == 200

    def test_password_update_missing_current(self, employee_client):
        resp = employee_client.patch(
            "/users/3/password",
            json={"new_password": "newpass1234"},
        )
        assert resp.status_code == 422  # Pydantic validation


class TestAdminPasswordReset:
    def test_admin_resets_password(self, admin_client, db):
        user = make_db_user(db, password="oldpass123")
        db.commit()
        resp = admin_client.patch(
            f"/users/{user.id}/reset-password",
            json={"new_password": "newpass1234"},
        )
        assert resp.status_code == 200

    def test_short_password_rejected(self, admin_client, db):
        user = make_db_user(db, password="oldpass123")
        db.commit()
        resp = admin_client.patch(
            f"/users/{user.id}/reset-password",
            json={"new_password": "short"},
        )
        assert resp.status_code == 422


class TestCreateUserRoute:
    def test_admin_creates_user(self, admin_client):
        payload = {
            "name": "John Doe", "username": "johndoe",
            "email": "john@example.com", "password": "password123",
            "role": "employee",
        }
        resp = admin_client.post("/auth/register", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "john@example.com"
        assert "password" not in data
        assert "hashed_password" not in data

    def test_employee_cannot_create_user(self, employee_client):
        payload = {
            "name": "John", "username": "johndoe",
            "email": "john@example.com", "password": "password123",
            "role": "employee",
        }
        resp = employee_client.post("/auth/register", json=payload)
        assert resp.status_code == 403