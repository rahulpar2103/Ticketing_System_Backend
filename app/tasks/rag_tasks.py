from app.core.celery_app import celery_app
from app.db.database import session_local
from app.models.ticketModel import Ticket
from app.models.commentModel import Comment
from app.services import rag_service
from app.core.logger import logger

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def index_ticket_task(self, ticket_id: int):
    """Asynchronously index a ticket into the vector store."""
    logger.info(f"Triggering background indexing for ticket {ticket_id}")
    db = session_local()
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if ticket:
            success = rag_service.index_ticket(db, ticket)
            if not success:
                raise Exception("Failed to generate embedding or index ticket")
        else:
            logger.warning(f"Ticket {ticket_id} not found for indexing")
    except Exception as exc:
        logger.error(f"Error indexing ticket {ticket_id}: {exc}")
        raise self.retry(exc=exc)
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def index_comment_task(self, comment_id: int):
    """Asynchronously index a comment into the vector store."""
    logger.info(f"Triggering background indexing for comment {comment_id}")
    db = session_local()
    try:
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if comment:
            success = rag_service.index_comment(db, comment)
            if not success:
                raise Exception("Failed to generate embedding or index comment")
        else:
            logger.warning(f"Comment {comment_id} not found for indexing")
    except Exception as exc:
        logger.error(f"Error indexing comment {comment_id}: {exc}")
        raise self.retry(exc=exc)
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def delete_ticket_vector_task(self, ticket_id: int):
    """Delete a ticket vector document."""
    db = session_local()
    try:
        rag_service.delete_vector_document(db, "ticket", ticket_id)
    except Exception as exc:
        logger.error(f"Error deleting ticket vector {ticket_id}: {exc}")
        raise self.retry(exc=exc)
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def delete_comment_vector_task(self, comment_id: int):
    """Delete a comment vector document."""
    db = session_local()
    try:
        rag_service.delete_vector_document(db, "comment", comment_id)
    except Exception as exc:
        logger.error(f"Error deleting comment vector {comment_id}: {exc}")
        raise self.retry(exc=exc)
    finally:
        db.close()
