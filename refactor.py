import os
import re

DEPENDENCIES_FILE = "app/dependencies/user.py"

def update_dependencies():
    with open(DEPENDENCIES_FILE, "r") as f:
        content = f.read()

    if "def require_admin" not in content:
        addition = """
from app.core.exceptions import PermissionDeniedException
from app.models.userModel import UserRole

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise PermissionDeniedException("Not allowed to access this endpoint")
    return current_user

def require_agent(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.agent:
        raise PermissionDeniedException("Not allowed to access this endpoint")
    return current_user

def require_employee(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.employee:
        raise PermissionDeniedException("Not allowed to access this endpoint")
    return current_user
"""
        with open(DEPENDENCIES_FILE, "a") as f:
            f.write(addition)

update_dependencies()
print("Updated dependencies.")
