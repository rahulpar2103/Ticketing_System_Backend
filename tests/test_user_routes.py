from tests.conftest import make_fake_user
from app.dependencies.user import get_current_user
from app.main import app
from app.models.userModel import UserRole

def test_create_user_route(client):
    payload = {
        "name": "John Doe",
        "username": "johndoe",
        "email": "john@example.com",
        "password": "password123",
        "role": "employee"
    }
    response = client.post("/create", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "john@example.com"
    assert data["username"] == "johndoe"
    assert "password" not in data
    assert "hashed_password" not in data

def test_create_user_as_employee_is_forbidden(client):
    app.dependency_overrides[get_current_user] = lambda: make_fake_user(UserRole.employee)
    payload = {
        "name": "John Doe",
        "username": "johndoe",
        "email": "john@example.com",
        "password": "password123",
        "role": "employee"
    }
    response = client.post("/create", json=payload)
    assert response.status_code == 403