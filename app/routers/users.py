from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.limiter import limiter
from app.dependencies.db import get_db
from app.dependencies.user import get_current_user
from app.models.userModel import User, UserRole
from app.schemas.userSchema import UserResponse, UserUpdate, PasswordUpdate, AdminPasswordReset
from app.services.userServices.admin import user_service_admin
from app.services.userServices.agent import user_service_agent
from app.services.userServices.employee import user_service_employee

router = APIRouter(prefix="/users", tags=["Users"])


def _get_user_service(role: UserRole):
    """Return the appropriate user service based on the user's role."""
    services = {
        UserRole.admin: user_service_admin,
        UserRole.agent: user_service_agent,
        UserRole.employee: user_service_employee,
    }
    return services[role]


@router.get("", response_model=list[UserResponse])
@limiter.limit("30/minute")
def get_all_users(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10,
    offset: int = 0,
):
    """List all users. Admin only."""
    return user_service_admin.get_all_users(current_user, db, limit, offset)


@router.get("/{user_id}", response_model=UserResponse)
@limiter.limit("30/minute")
def get_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a user by ID. Behavior varies by role."""
    service = _get_user_service(current_user.role)
    return service.get_user(current_user, user_id, db)


@router.patch("/{user_id}", response_model=dict)
@limiter.limit("20/minute")
def update_user(
    request: Request,
    user_id: int,
    user: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a user. Admin only."""
    return user_service_admin.update_user(current_user, user_id, user, db)


@router.delete("/{user_id}", response_model=dict)
@limiter.limit("20/minute")
def delete_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft-delete a user. Admin only."""
    return user_service_admin.delete_user(current_user, user_id, db)


@router.patch("/{user_id}/password", response_model=dict)
@limiter.limit("5/minute")
def update_own_password(
    request: Request,
    user_id: int,
    user_update: PasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change your own password. Requires current password. Agent/Employee only."""
    service = _get_user_service(current_user.role)
    return service.update_user_password(current_user, user_id, user_update, db)


@router.patch("/{user_id}/reset-password", response_model=dict)
@limiter.limit("5/minute")
def admin_reset_password(
    request: Request,
    user_id: int,
    user_update: AdminPasswordReset,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reset any user's password without current password. Admin only."""
    return user_service_admin.update_user_password(current_user, user_id, user_update, db)
