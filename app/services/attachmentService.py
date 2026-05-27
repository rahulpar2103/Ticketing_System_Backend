"""
Attachment service — handles presigned upload/download URLs, confirmation,
listing, and deletion of file attachments on tickets.
"""

import uuid
import re
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.attachmentModel import Attachment, AttachmentStatus
from app.models.ticketModel import Ticket
from app.models.userModel import User, UserRole
from app.schemas.attachmentSchema import (
    AttachmentPresignRequest,
    AttachmentPresignResponse,
    AttachmentResponse,
    MAX_ATTACHMENTS_PER_TICKET,
)
from app.core.s3 import (
    generate_presigned_upload_url,
    generate_presigned_download_url,
    head_s3_object,
    delete_s3_object,
)
from app.db.redis import safe_delete, delete_by_prefix
from app.core.exceptions import (
    NotFoundException,
    PermissionDeniedException,
    ValidationException,
)
from app.core.logger import logger


# Helpers

def _sanitize_filename(filename: str) -> str:
    """Strip path separators and non-ASCII chars to produce a safe S3 key segment."""
    name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    name = re.sub(r"[^\w.\-]", "_", name)
    return name[:200]


def _get_ticket_or_404(db: Session, ticket_id: int) -> Ticket:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.is_active == True).first()
    if not ticket:
        raise NotFoundException(f"Ticket {ticket_id} not found")
    return ticket


def _check_ticket_access(ticket: Ticket, user: User) -> None:
    """Verify the user has access to the ticket (can view it)."""
    if user.role == UserRole.admin:
        return
    if ticket.created_by == user.id:
        return
    if ticket.assigned_to == user.id:
        return
    if user.role == UserRole.agent and ticket.team_id and user.team_id == ticket.team_id:
        return
    raise PermissionDeniedException("You do not have access to this ticket")


def _build_response(attachment: Attachment) -> AttachmentResponse:
    download_url = None
    if attachment.status == AttachmentStatus.uploaded:
        download_url = generate_presigned_download_url(attachment.s3_key)

    return AttachmentResponse(
        id=attachment.id,
        ticket_id=attachment.ticket_id,
        uploaded_by=attachment.uploaded_by,
        uploaded_by_username=attachment.uploader.username if attachment.uploader else None,
        filename=attachment.filename,
        content_type=attachment.content_type,
        file_size=attachment.file_size,
        download_url=download_url,
        created_at=attachment.created_at,
    )


# Service functions

def presign_upload(
    ticket_id: int,
    body: AttachmentPresignRequest,
    db: Session,
    current_user: User,
) -> AttachmentPresignResponse:
    """Create a presigned PUT URL so the client can upload directly to S3."""
    ticket = _get_ticket_or_404(db, ticket_id)
    _check_ticket_access(ticket, current_user)

    # Check attachment limit
    existing_count = (
        db.execute(
            select(func.count(Attachment.id)).where(
                Attachment.ticket_id == ticket_id,
                Attachment.status == AttachmentStatus.uploaded,
            )
        )
        .scalar_one()
    )
    if existing_count >= MAX_ATTACHMENTS_PER_TICKET:
        raise ValidationException(
            f"Maximum of {MAX_ATTACHMENTS_PER_TICKET} attachments per ticket reached"
        )

    # Build S3 key
    safe_name = _sanitize_filename(body.filename)
    s3_key = f"attachments/{ticket_id}/{uuid.uuid4().hex}_{safe_name}"

    # Create DB record (pending)
    attachment = Attachment(
        ticket_id=ticket_id,
        uploaded_by=current_user.id,
        filename=body.filename.strip(),
        s3_key=s3_key,
        content_type=body.content_type,
        status=AttachmentStatus.pending,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    upload_url = generate_presigned_upload_url(s3_key, body.content_type)

    logger.info(
        f"Presigned upload URL generated for ticket {ticket_id} by user {current_user.id}",
        extra={"ticket_id": ticket_id, "attachment_id": attachment.id, "attachment_filename": body.filename},
    )

    return AttachmentPresignResponse(
        attachment_id=attachment.id,
        upload_url=upload_url,
        s3_key=s3_key,
    )


def confirm_upload(
    ticket_id: int,
    attachment_id: int,
    db: Session,
    current_user: User,
) -> AttachmentResponse:
    """Mark an attachment as uploaded after the client finishes the S3 PUT."""
    ticket = _get_ticket_or_404(db, ticket_id)
    _check_ticket_access(ticket, current_user)

    attachment = (
        db.query(Attachment)
        .filter(
            Attachment.id == attachment_id,
            Attachment.ticket_id == ticket_id,
        )
        .first()
    )
    if not attachment:
        raise NotFoundException(f"Attachment {attachment_id} not found on ticket {ticket_id}")

    if attachment.status == AttachmentStatus.uploaded:
        raise ValidationException("Attachment is already confirmed")

    # Verify the file actually exists in S3
    meta = head_s3_object(attachment.s3_key)
    if meta is None:
        raise ValidationException(
            "File not found in storage. Please upload the file before confirming."
        )

    attachment.status = AttachmentStatus.uploaded
    attachment.file_size = meta.get("ContentLength")
    db.commit()
    db.refresh(attachment)

    # Invalidate ticket cache so attachment_count updates
    safe_delete(f"ticket:{ticket_id}")
    delete_by_prefix("tickets:")

    logger.info(
        f"Attachment {attachment_id} confirmed for ticket {ticket_id}",
        extra={"ticket_id": ticket_id, "attachment_id": attachment_id},
    )

    return _build_response(attachment)


def list_attachments(
    ticket_id: int,
    db: Session,
    current_user: User,
) -> list[AttachmentResponse]:
    """Return all confirmed attachments for a ticket with presigned download URLs."""
    ticket = _get_ticket_or_404(db, ticket_id)
    _check_ticket_access(ticket, current_user)

    attachments = (
        db.query(Attachment)
        .filter(
            Attachment.ticket_id == ticket_id,
            Attachment.status == AttachmentStatus.uploaded,
        )
        .order_by(Attachment.created_at.asc())
        .all()
    )
    return [_build_response(a) for a in attachments]


def get_download_url(
    ticket_id: int,
    attachment_id: int,
    db: Session,
    current_user: User,
) -> dict:
    """Return a fresh presigned download URL for a single attachment."""
    ticket = _get_ticket_or_404(db, ticket_id)
    _check_ticket_access(ticket, current_user)

    attachment = (
        db.query(Attachment)
        .filter(
            Attachment.id == attachment_id,
            Attachment.ticket_id == ticket_id,
            Attachment.status == AttachmentStatus.uploaded,
        )
        .first()
    )
    if not attachment:
        raise NotFoundException(f"Attachment {attachment_id} not found")

    url = generate_presigned_download_url(attachment.s3_key)
    return {"download_url": url, "filename": attachment.filename}


def delete_attachment(
    ticket_id: int,
    attachment_id: int,
    db: Session,
    current_user: User,
) -> dict:
    """Delete an attachment from S3 and the database. Only uploader or admin may delete."""
    ticket = _get_ticket_or_404(db, ticket_id)
    _check_ticket_access(ticket, current_user)

    attachment = (
        db.query(Attachment)
        .filter(
            Attachment.id == attachment_id,
            Attachment.ticket_id == ticket_id,
        )
        .first()
    )
    if not attachment:
        raise NotFoundException(f"Attachment {attachment_id} not found")

    # Permission check: only the uploader or an admin can delete
    if current_user.role != UserRole.admin and attachment.uploaded_by != current_user.id:
        raise PermissionDeniedException("Only the uploader or an admin can delete this attachment")

    # Delete from S3 (best-effort — if it fails, the DB record is still removed)
    try:
        delete_s3_object(attachment.s3_key)
    except Exception:
        logger.warning(
            f"Failed to delete S3 object {attachment.s3_key} for attachment {attachment_id}",
            exc_info=True,
        )

    db.delete(attachment)
    db.commit()

    # Invalidate ticket cache so attachment_count updates
    safe_delete(f"ticket:{ticket_id}")
    delete_by_prefix("tickets:")

    logger.info(
        f"Attachment {attachment_id} deleted from ticket {ticket_id} by user {current_user.id}",
        extra={"ticket_id": ticket_id, "attachment_id": attachment_id},
    )

    return {"detail": f"Attachment {attachment_id} deleted successfully"}
