"""
HTTP tests for Auth routes (/auth/*).
"""
import pytest
from tests.conftest import make_db_user
from app.models.userModel import UserRole
from app.core.security import hash_password


class TestLoginRoute:
    def test_login_success(self, client, db):
        make_db_user(db, username="loginuser", email="login@t.com",
                     password="StrongP@ss123!", role=UserRole.employee)
        db.commit()
        resp = client.post("/auth/login", data={
            "username": "loginuser", "password": "StrongP@ss123!"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client, db):
        make_db_user(db, username="loginuser", email="login@t.com",
                     password="StrongP@ss123!")
        db.commit()
        resp = client.post("/auth/login", data={
            "username": "loginuser", "password": "wrongpass1"})
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/auth/login", data={
            "username": "nobody", "password": "StrongP@ss123!"})
        assert resp.status_code == 401

    def test_login_with_email(self, client, db):
        make_db_user(db, username="loginuser", email="login@t.com",
                     password="StrongP@ss123!")
        db.commit()
        resp = client.post("/auth/login", data={
            "username": "login@t.com", "password": "StrongP@ss123!"})
        assert resp.status_code == 200


class TestRegisterRoute:
    def test_admin_registers_user(self, admin_client):
        resp = admin_client.post("/auth/register", json={
            "name": "New User", "username": "newuser",
            "email": "new@example.com", "password": "StrongP@ss123!",
            "role": "employee",
        })
        assert resp.status_code == 201
        assert resp.json()["username"] == "newuser"

    def test_employee_cannot_register(self, employee_client):
        resp = employee_client.post("/auth/register", json={
            "name": "New User", "username": "newuser",
            "email": "new@example.com", "password": "StrongP@ss123!",
            "role": "employee",
        })
        assert resp.status_code == 403

    def test_short_password_rejected(self, admin_client):
        resp = admin_client.post("/auth/register", json={
            "name": "New User", "username": "newuser",
            "email": "new@example.com", "password": "Sh0rt!",
            "role": "employee",
        })
        assert resp.status_code == 422

    def test_invalid_email_rejected(self, admin_client):
        resp = admin_client.post("/auth/register", json={
            "name": "New User", "username": "newuser",
            "email": "not-valid", "password": "StrongP@ss123!",
            "role": "employee",
        })
        assert resp.status_code == 422

    def test_duplicate_registration(self, admin_client):
        payload = {
            "name": "User", "username": "dupuser",
            "email": "dup@example.com", "password": "StrongP@ss123!",
            "role": "employee",
        }
        admin_client.post("/auth/register", json=payload)
        resp = admin_client.post("/auth/register", json=payload)
        assert resp.status_code == 400


class TestLogoutRoute:
    def test_logout_success(self, db):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.dependencies.db import get_db
        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app, raise_server_exceptions=False)

        # 1. Create a user and login
        make_db_user(db, username="logoutuser", email="logout@t.com", password="StrongP@ss123!")
        db.commit()
        resp = client.post("/auth/login", data={"username": "logoutuser", "password": "StrongP@ss123!"})
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Verify token works
        me_resp = client.get("/users/me", headers=headers)
        assert me_resp.status_code == 200
        
        # 3. Logout
        logout_resp = client.post("/auth/logout", headers=headers)
        assert logout_resp.status_code == 200
        assert "logged out" in logout_resp.json()["message"]
        
        # 4. Verify token no longer works
        me_resp2 = client.get("/users/me", headers=headers)
        assert me_resp2.status_code == 401
        
        app.dependency_overrides.clear()
