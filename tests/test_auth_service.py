from app.services.userServices.auth import auth_service
from app.schemas.userSchema import UserCreate
from app.models.userModel import UserRole, User
from app.core.exceptions import AlreadyExistsException
import pytest

# A fake admin user to pass as current_user
def make_admin():
    user = User()
    user.id = 1
    user.role = UserRole.admin
    return user

def test_create_user_persists_to_database(db):
    # Arrange
    admin = make_admin()
    user_data = UserCreate(
        name="Test User",
        username="testuser",
        email="test@example.com",
        password="password123",
        role=UserRole.employee,
    )

    # Act
    created = auth_service.create_user(admin, user_data, db)

    # Assert
    fetched = db.query(User).filter(User.email == "test@example.com").first()
    assert fetched is not None
    assert fetched.username == "testuser"
    assert fetched.hashed_password != "password123"  # must be hashed

    
def test_create_user_duplicate_email_raises(db):
    admin = make_admin()
    user_data = UserCreate(
        name="Test User",
        username="testuser",
        email="test@example.com",
        password="password123",
        role=UserRole.employee,
    )
    auth_service.create_user(admin, user_data, db)

    with pytest.raises(AlreadyExistsException):
        auth_service.create_user(admin, user_data, db)

def test_create_user_invalid_username_raises(db):
    admin = make_admin()
    user_data = UserCreate(
        name="Test User",
        username="test@user",
        email="another@example.com",
        password="password123",
        role=UserRole.employee,
    )

    with pytest.raises(AlreadyExistsException):
        auth_service.create_user(admin, user_data, db)
