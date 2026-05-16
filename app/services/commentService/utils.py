# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session, joinedload
from app.models.commentModel import Comment
from app.schemas.commentSchema import CommentResponse


def _load_comment(db: Session, comment_id: int) -> Comment | None:
    return (
        db.query(Comment)
        .options(joinedload(Comment.user))
        .filter(Comment.id == comment_id)
        .first()
    )

def _load_comments(query):
    return query.options(joinedload(Comment.user))

def _build_response(comment: Comment) -> CommentResponse:
    return CommentResponse(
        id=comment.id,
        comment=comment.comment,
        ticket_id=comment.ticket_id,
        user_id=comment.user_id,
        username=comment.user.username if comment.user else None,
        is_edited=comment.is_edited,
        created_at=comment.created_at,
    )