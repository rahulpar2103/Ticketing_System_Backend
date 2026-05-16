# pyrefly: ignore [missing-import]
import json
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from app.db.redis import redis_client, delete_by_prefix
from app.models.commentModel import Comment
from app.models.ticketModel import Ticket
from app.models.userModel import User
from app.schemas.commentSchema import CommentCreate, CommentUpdate, CommentResponse
from app.core.exceptions import NotFoundException, PermissionDeniedException
from app.services.commentService.utils import _build_response, _load_comment, _load_comments


def _ticket_accessible(ticket: Ticket, current_user: User) -> bool:
    return (
        ticket.created_by == current_user.id
        or ticket.assigned_to == current_user.id
        or (current_user.team_id is not None and ticket.team_id == current_user.team_id)
    )


class AgentCommentService:

    @staticmethod
    def create_comment(ticket_id: int, body: CommentCreate, db: Session, current_user: User):
        if current_user.role.value != "agent":
            raise PermissionDeniedException("Not allowed to access this endpoint")
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise NotFoundException(f"Ticket {ticket_id} not found")
        if not _ticket_accessible(ticket, current_user):
            raise PermissionDeniedException("You do not have access to this ticket")
        comment = Comment(comment=body.comment, ticket_id=ticket_id, user_id=current_user.id)
        db.add(comment)
        db.commit()
        comment = _load_comment(db, comment.id)
        delete_by_prefix(f"comments:ticket:{ticket_id}:")
        return _build_response(comment)

    @staticmethod
    def get_ticket_comments(ticket_id: int, db: Session, current_user: User, limit: int, offset: int):
        if current_user.role.value != "agent":
            raise PermissionDeniedException("Not allowed to access this endpoint")
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise NotFoundException(f"Ticket {ticket_id} not found")
        if not _ticket_accessible(ticket, current_user):
            raise PermissionDeniedException("You do not have access to this ticket")
        cache_key = f"comments:ticket:{ticket_id}:{limit}:{offset}"
        cached = redis_client.get(cache_key)
        if cached:
            return [CommentResponse.model_validate(c) for c in json.loads(cached)]
        comments = _load_comments(
            db.query(Comment).filter(Comment.ticket_id == ticket_id)
        ).limit(limit).offset(offset).all()
        responses = [_build_response(c) for c in comments]
        redis_client.setex(cache_key, 60 * 60, json.dumps([r.model_dump(mode="json") for r in responses]))
        return responses

    @staticmethod
    def get_comment(comment_id: int, db: Session, current_user: User):
        if current_user.role.value != "agent":
            raise PermissionDeniedException("Not allowed to access this endpoint")
        comment = _load_comment(db, comment_id)
        if not comment:
            raise NotFoundException(f"Comment {comment_id} not found")
        ticket = db.query(Ticket).filter(Ticket.id == comment.ticket_id).first()
        if not _ticket_accessible(ticket, current_user):
            raise PermissionDeniedException("You do not have access to this comment")
        return _build_response(comment)

    @staticmethod
    def update_comment(comment_id: int, body: CommentUpdate, db: Session, current_user: User):
        if current_user.role.value != "agent":
            raise PermissionDeniedException("Not allowed to access this endpoint")
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if not comment:
            raise NotFoundException(f"Comment {comment_id} not found")
        if comment.user_id != current_user.id:
            raise PermissionDeniedException("You can only edit your own comments")
        comment.comment = body.comment
        comment.is_edited = True
        db.commit()
        comment = _load_comment(db, comment_id)
        delete_by_prefix(f"comments:ticket:{comment.ticket_id}:")
        return _build_response(comment)

    @staticmethod
    def delete_comment(comment_id: int, db: Session, current_user: User):
        if current_user.role.value != "agent":
            raise PermissionDeniedException("Not allowed to access this endpoint")
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if not comment:
            raise NotFoundException(f"Comment {comment_id} not found")
        if comment.user_id != current_user.id:
            raise PermissionDeniedException("You can only delete your own comments")
        ticket_id = comment.ticket_id
        db.delete(comment)
        db.commit()
        delete_by_prefix(f"comments:ticket:{ticket_id}:")
        return {"message": f"Comment {comment_id} deleted successfully"}


agent_comment_service = AgentCommentService()