from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session
from app.core.limiter import limiter
from app.dependencies.db import get_db
from app.dependencies.user import get_current_user
from app.models.userModel import User, UserRole
from app.schemas.commentSchema import CommentCreate, CommentUpdate, CommentResponse
from app.schemas.pagination import PaginatedResponse
from app.services.commentService.admin import admin_comment_service
from app.services.commentService.agent import agent_comment_service
from app.services.commentService.employee import employee_comment_service

router = APIRouter(tags=["Comments"])


def _get_comment_service(role: UserRole):
    """Return the appropriate comment service based on the user's role."""
    services = {
        UserRole.admin: admin_comment_service,
        UserRole.agent: agent_comment_service,
        UserRole.employee: employee_comment_service,
    }
    return services[role]


# Ticket-scoped comments

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
    service = _get_comment_service(current_user.role)
    new_comment = service.create_comment(ticket_id, body, db, current_user)
    try:
        from app.tasks.rag_tasks import index_comment_task
        index_comment_task.delay(new_comment.id)
    except Exception as e:
        from app.core.logger import logger
        logger.error(f"RAG indexing trigger failed for comment create: {e}")
    try:
        from fastapi.encoders import jsonable_encoder
        from app.db.redis import redis_client
        import json
        payload = {
            "type": "COMMENT_CREATED",
            "data": {
                "ticket_id": ticket_id,
                "comment": jsonable_encoder(new_comment)
            }
        }
        redis_client.publish("ticket_updates", json.dumps(payload))
    except Exception as e:
        from app.core.logger import logger
        logger.error(f"WebSocket publish failed for comment create: {e}")
    return new_comment


@router.get("/tickets/{ticket_id}/comments", response_model=PaginatedResponse[CommentResponse])
@limiter.limit("30/minute")
def get_ticket_comments(
    request: Request,
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at", description="Sort field: created_at, updated_at"),
    order: str = Query("asc", description="Sort order: asc or desc"),
):
    """Get all comments for a ticket with sorting. Behavior varies by role."""
    service = _get_comment_service(current_user.role)
    return service.get_ticket_comments(ticket_id, db, current_user, limit, offset, sort_by, order)


# Individual comment actions

@router.get("/comments/{comment_id}", response_model=CommentResponse)
@limiter.limit("30/minute")
def get_comment(
    request: Request,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single comment. Behavior varies by role."""
    service = _get_comment_service(current_user.role)
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
    service = _get_comment_service(current_user.role)
    updated_comment = service.update_comment(comment_id, body, db, current_user)
    try:
        from app.tasks.rag_tasks import index_comment_task
        index_comment_task.delay(comment_id)
    except Exception as e:
        from app.core.logger import logger
        logger.error(f"RAG indexing trigger failed for comment update: {e}")
    return updated_comment


@router.delete("/comments/{comment_id}", response_model=dict)
@limiter.limit("20/minute")
def delete_comment(
    request: Request,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a comment. Ownership rules vary by role."""
    service = _get_comment_service(current_user.role)
    result = service.delete_comment(comment_id, db, current_user)
    try:
        from app.tasks.rag_tasks import delete_comment_vector_task
        delete_comment_vector_task.delay(comment_id)
    except Exception as e:
        from app.core.logger import logger
        logger.error(f"RAG indexing delete trigger failed for comment: {e}")
    try:
        from app.db.redis import redis_client
        import json
        payload = {
            "type": "COMMENT_DELETED",
            "data": {
                "comment_id": comment_id
            }
        }
        redis_client.publish("ticket_updates", json.dumps(payload))
    except Exception as e:
        from app.core.logger import logger
        logger.error(f"WebSocket publish failed for comment delete: {e}")
    return result
