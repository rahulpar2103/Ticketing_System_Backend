import json
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from app.db.redis import safe_get, safe_setex, delete_by_prefix
from app.models.commentModel import Comment
from app.models.ticketModel import Ticket
from app.core.security import require_role
from app.models.userModel import User, UserRole
from app.schemas.commentSchema import CommentCreate, CommentUpdate, CommentResponse
from app.core.exceptions import NotFoundException, PermissionDeniedException, ValidationException
from app.services.commentService.utils import _build_response, _load_comment, _load_comments

COMMENT_SORTABLE_FIELDS = {
    "created_at": Comment.created_at,
    "updated_at": Comment.updated_at,
}


class AdminCommentService:

    def create_comment(self, ticket_id: int, body: CommentCreate, db: Session, current_user: User):
        require_role(current_user, UserRole.admin)
        if not db.query(Ticket).filter(Ticket.id == ticket_id).first():
            raise NotFoundException(f"Ticket {ticket_id} not found")
        comment = Comment(
            comment=body.comment,
            ticket_id=ticket_id,
            user_id=current_user.id,
        )
        db.add(comment)
        db.commit()
        comment = _load_comment(db, comment.id)
        delete_by_prefix(f"comments:ticket:{ticket_id}:")
        return _build_response(comment)

    def get_ticket_comments(
        self, ticket_id: int, db: Session, current_user: User, limit: int, offset: int,
        sort_by: str = "created_at", order: str = "asc",
    ):
        require_role(current_user, UserRole.admin)
        if not db.query(Ticket).filter(Ticket.id == ticket_id).first():
            raise NotFoundException(f"Ticket {ticket_id} not found")

        query = db.query(Comment).filter(Comment.ticket_id == ticket_id)

        # Sorting
        column = COMMENT_SORTABLE_FIELDS.get(sort_by)
        if column is None:
            raise ValidationException(
                f"Invalid sort_by '{sort_by}'. Allowed: {list(COMMENT_SORTABLE_FIELDS.keys())}"
            )
        if order not in ("asc", "desc"):
            raise ValidationException("Invalid order. Allowed: 'asc', 'desc'")
        order_func = asc if order == "asc" else desc
        query = query.order_by(order_func(column))

        total = query.count()
        comments = _load_comments(query).limit(limit).offset(offset).all()
        items = [_build_response(c) for c in comments]
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total,
        }

    def get_comment(self, comment_id: int, db: Session, current_user: User):
        require_role(current_user, UserRole.admin)
        comment = _load_comment(db, comment_id)
        if not comment:
            raise NotFoundException(f"Comment {comment_id} not found")
        return _build_response(comment)

    def update_comment(self, comment_id: int, body: CommentUpdate, db: Session, current_user: User):
        require_role(current_user, UserRole.admin)
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if not comment:
            raise NotFoundException(f"Comment {comment_id} not found")
        comment.comment = body.comment
        comment.is_edited = True
        db.commit()
        comment = _load_comment(db, comment_id)
        delete_by_prefix(f"comments:ticket:{comment.ticket_id}:")
        return _build_response(comment)

    def delete_comment(self, comment_id: int, db: Session, current_user: User):
        require_role(current_user, UserRole.admin)
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if not comment:
            raise NotFoundException(f"Comment {comment_id} not found")
        ticket_id = comment.ticket_id
        db.delete(comment)
        db.commit()
        delete_by_prefix(f"comments:ticket:{ticket_id}:")
        return {"message": f"Comment {comment_id} deleted successfully"}


admin_comment_service = AdminCommentService()