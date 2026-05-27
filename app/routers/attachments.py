from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.limiter import limiter
from app.dependencies.db import get_db
from app.dependencies.user import get_current_user
from app.models.userModel import User
from app.schemas.attachmentSchema import (
    AttachmentPresignRequest,
    AttachmentPresignResponse,
    AttachmentResponse,
)
from app.services import attachmentService

router = APIRouter(tags=["Attachments"])


@router.post(
    "/tickets/{ticket_id}/attachments/presign",
    status_code=201,
    response_model=AttachmentPresignResponse,
)
@limiter.limit("20/minute")
def presign_upload(
    request: Request,
    ticket_id: int,
    body: AttachmentPresignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a presigned S3 URL to upload a file attachment.
    After uploading, call the confirm endpoint to finalize.
    """
    return attachmentService.presign_upload(ticket_id, body, db, current_user)


@router.post(
    "/tickets/{ticket_id}/attachments/{attachment_id}/confirm",
    response_model=AttachmentResponse,
)
@limiter.limit("20/minute")
def confirm_upload(
    request: Request,
    ticket_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Confirm that a file has been uploaded to S3 successfully."""
    return attachmentService.confirm_upload(ticket_id, attachment_id, db, current_user)


@router.get(
    "/tickets/{ticket_id}/attachments",
    response_model=list[AttachmentResponse],
)
@limiter.limit("30/minute")
def list_attachments(
    request: Request,
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all confirmed attachments for a ticket with download URLs."""
    return attachmentService.list_attachments(ticket_id, db, current_user)


@router.get(
    "/tickets/{ticket_id}/attachments/{attachment_id}/download",
    response_model=dict,
)
@limiter.limit("30/minute")
def get_download_url(
    request: Request,
    ticket_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a fresh presigned download URL for a specific attachment."""
    return attachmentService.get_download_url(ticket_id, attachment_id, db, current_user)


@router.delete(
    "/tickets/{ticket_id}/attachments/{attachment_id}",
    response_model=dict,
)
@limiter.limit("20/minute")
def delete_attachment(
    request: Request,
    ticket_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an attachment. Only the uploader or an admin may delete."""
    return attachmentService.delete_attachment(ticket_id, attachment_id, db, current_user)
