from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.limiter import limiter
from app.dependencies.db import get_db
from app.dependencies.user import get_current_user
from app.models.userModel import User
from app.schemas.commentSchema import CommentCreate, CommentUpdate, CommentResponse
from app.services.commentService.admin import admin_comment_service

router = APIRouter(prefix="/comments/admin", tags=["Admin Comments"])

@router.post("/ticket/{ticket_id}", status_code=201, response_model=CommentResponse)
@limiter.limit("30/minute")
def create_comment(request: Request, ticket_id: int, body: CommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return admin_comment_service.create_comment(ticket_id, body, db, current_user)

@router.get("/ticket/{ticket_id}", response_model=list[CommentResponse])
@limiter.limit("30/minute")
def get_ticket_comments(request: Request, ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), limit: int = 10, offset: int = 0):
    return admin_comment_service.get_ticket_comments(ticket_id, db, current_user, limit, offset)

@router.get("/{comment_id}", response_model=CommentResponse)
@limiter.limit("30/minute")
def get_comment(request: Request, comment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return admin_comment_service.get_comment(comment_id, db, current_user)

@router.patch("/{comment_id}", response_model=CommentResponse)
@limiter.limit("20/minute")
def update_comment(request: Request, comment_id: int, body: CommentUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return admin_comment_service.update_comment(comment_id, body, db, current_user)

@router.delete("/{comment_id}", response_model=dict)
@limiter.limit("20/minute")
def delete_comment(request: Request, comment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return admin_comment_service.delete_comment(comment_id, db, current_user)