from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.limiter import limiter
from app.dependencies.db import get_db
from app.dependencies.user import get_current_user
from app.models.userModel import User
from app.schemas.commentSchema import CommentCreate, CommentUpdate, CommentResponse
from app.services.commentService.admin import admin_comment_service
from app.services.commentService.agent import agent_comment_service
from app.services.commentService.employee import employee_comment_service

router = APIRouter(tags=["Comments"])


def _get_comment_service(role: str):
    """Return the appropriate comment service based on the user's role."""
    services = {
        "admin": admin_comment_service,
        "agent": agent_comment_service,
        "employee": employee_comment_service,
    }
    return services[role]


# ------------------------------------------------------------------ #
# Ticket-scoped comment routes                                        #
# ------------------------------------------------------------------ #

@router.post("/tickets/{ticket_id}/comments", status_code=201, response_model=CommentResponse)
@limiter.limit("30/minute")
def create_comment(
    request: Request,
    ticket_id: int,
    body: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a comment on a ticket. Behavior varies by role."""
    service = _get_comment_service(current_user.role.value)
    return service.create_comment(ticket_id, body, db, current_user)


@router.get("/tickets/{ticket_id}/comments", response_model=list[CommentResponse])
@limiter.limit("30/minute")
def get_ticket_comments(
    request: Request,
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 10,
    offset: int = 0,
):
    """Get all comments for a ticket. Behavior varies by role."""
    service = _get_comment_service(current_user.role.value)
    return service.get_ticket_comments(ticket_id, db, current_user, limit, offset)


# ------------------------------------------------------------------ #
# Individual comment routes                                            #
# ------------------------------------------------------------------ #

@router.get("/comments/{comment_id}", response_model=CommentResponse)
@limiter.limit("30/minute")
def get_comment(
    request: Request,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single comment. Behavior varies by role."""
    service = _get_comment_service(current_user.role.value)
    return service.get_comment(comment_id, db, current_user)


@router.patch("/comments/{comment_id}", response_model=CommentResponse)
@limiter.limit("20/minute")
def update_comment(
    request: Request,
    comment_id: int,
    body: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a comment. Behavior varies by role."""
    service = _get_comment_service(current_user.role.value)
    return service.update_comment(comment_id, body, db, current_user)


@router.delete("/comments/{comment_id}", response_model=dict)
@limiter.limit("20/minute")
def delete_comment(
    request: Request,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a comment. Admin and agent only."""
    role = current_user.role.value
    if role == "admin":
        return admin_comment_service.delete_comment(comment_id, db, current_user)
    elif role == "agent":
        return agent_comment_service.delete_comment(comment_id, db, current_user)
    else:
        from app.core.exceptions import PermissionDeniedException
        raise PermissionDeniedException("Employees cannot delete comments")
