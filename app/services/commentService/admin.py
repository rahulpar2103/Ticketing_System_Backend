import json
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from app.db.redis import safe_get, safe_setex, delete_by_prefix
from app.models.commentModel import Comment
from app.models.ticketModel import Ticket
from app.models.userModel import User
from app.schemas.commentSchema import CommentCreate, CommentUpdate, CommentResponse
from app.core.exceptions import NotFoundException, PermissionDeniedException
from app.services.commentService.utils import _build_response, _load_comment, _load_comments


class AdminCommentService:

    @staticmethod
    def create_comment(ticket_id: int, body: CommentCreate, db: Session, current_user: User):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Not allowed to access this endpoint")
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

    @staticmethod
    def get_ticket_comments(ticket_id: int, db: Session, current_user: User, limit: int, offset: int):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Not allowed to access this endpoint")
        if not db.query(Ticket).filter(Ticket.id == ticket_id).first():
            raise NotFoundException(f"Ticket {ticket_id} not found")
        cache_key = f"comments:ticket:{ticket_id}:{limit}:{offset}"
        cached = safe_get(cache_key)
        if cached:
            return [CommentResponse.model_validate(c) for c in json.loads(cached)]
        comments = _load_comments(
            db.query(Comment).filter(Comment.ticket_id == ticket_id)
        ).limit(limit).offset(offset).all()
        responses = [_build_response(c) for c in comments]
        safe_setex(cache_key, 60 * 60, json.dumps([r.model_dump(mode="json") for r in responses]))
        return responses

    @staticmethod
    def get_comment(comment_id: int, db: Session, current_user: User):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Not allowed to access this endpoint")
        comment = _load_comment(db, comment_id)
        if not comment:
            raise NotFoundException(f"Comment {comment_id} not found")
        return _build_response(comment)

    @staticmethod
    def update_comment(comment_id: int, body: CommentUpdate, db: Session, current_user: User):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Not allowed to access this endpoint")
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if not comment:
            raise NotFoundException(f"Comment {comment_id} not found")
        comment.comment = body.comment
        comment.is_edited = True
        db.commit()
        comment = _load_comment(db, comment_id)
        delete_by_prefix(f"comments:ticket:{comment.ticket_id}:")
        return _build_response(comment)

    @staticmethod
    def delete_comment(comment_id: int, db: Session, current_user: User):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Not allowed to access this endpoint")
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if not comment:
            raise NotFoundException(f"Comment {comment_id} not found")
        ticket_id = comment.ticket_id
        db.delete(comment)
        db.commit()
        delete_by_prefix(f"comments:ticket:{ticket_id}:")
        return {"message": f"Comment {comment_id} deleted successfully"}


admin_comment_service = AdminCommentService()