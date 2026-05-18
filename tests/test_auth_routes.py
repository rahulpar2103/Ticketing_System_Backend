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
                     password="password123", role=UserRole.employee)
        db.commit()
        resp = client.post("/auth/login", data={
            "username": "loginuser", "password": "password123"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client, db):
        make_db_user(db, username="loginuser", email="login@t.com",
                     password="password123")
        db.commit()
        resp = client.post("/auth/login", data={
            "username": "loginuser", "password": "wrongpass1"})
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/auth/login", data={
            "username": "nobody", "password": "password123"})
        assert resp.status_code == 401

    def test_login_with_email(self, client, db):
        make_db_user(db, username="loginuser", email="login@t.com",
                     password="password123")
        db.commit()
        resp = client.post("/auth/login", data={
            "username": "login@t.com", "password": "password123"})
        assert resp.status_code == 200


class TestRegisterRoute:
    def test_admin_registers_user(self, admin_client):
        resp = admin_client.post("/auth/register", json={
            "name": "New User", "username": "newuser",
            "email": "new@example.com", "password": "password123",
            "role": "employee",
        })
        assert resp.status_code == 201
        assert resp.json()["username"] == "newuser"

    def test_employee_cannot_register(self, employee_client):
        resp = employee_client.post("/auth/register", json={
            "name": "New User", "username": "newuser",
            "email": "new@example.com", "password": "password123",
            "role": "employee",
        })
        assert resp.status_code == 403

    def test_short_password_rejected(self, admin_client):
        resp = admin_client.post("/auth/register", json={
            "name": "New User", "username": "newuser",
            "email": "new@example.com", "password": "short",
            "role": "employee",
        })
        assert resp.status_code == 422

    def test_invalid_email_rejected(self, admin_client):
        resp = admin_client.post("/auth/register", json={
            "name": "New User", "username": "newuser",
            "email": "not-valid", "password": "password123",
            "role": "employee",
        })
        assert resp.status_code == 422

    def test_duplicate_registration(self, admin_client):
        payload = {
            "name": "User", "username": "dupuser",
            "email": "dup@example.com", "password": "password123",
            "role": "employee",
        }
        admin_client.post("/auth/register", json=payload)
        resp = admin_client.post("/auth/register", json=payload)
        assert resp.status_code == 400
