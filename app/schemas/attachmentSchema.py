from pydantic import BaseModel, field_validator
from datetime import datetime


# ── Allowed content types ────────────────────────────────────────────────────
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/pdf",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_ATTACHMENTS_PER_TICKET = 10


# ── Request schemas ─────────────────────────────────────────────────────────

class AttachmentPresignRequest(BaseModel):
    """Request body to obtain a presigned upload URL."""
    filename: str
    content_type: str

    @field_validator("filename", mode="before")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Filename cannot be empty")
        v = v.strip()
        if len(v) > 255:
            raise ValueError("Filename cannot exceed 255 characters")
        return v

    @field_validator("content_type", mode="before")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Content type cannot be empty")
        v = v.strip().lower()
        if v not in ALLOWED_CONTENT_TYPES:
            raise ValueError(
                f"Unsupported content type '{v}'. Allowed: {sorted(ALLOWED_CONTENT_TYPES)}"
            )
        return v


# ── Response schemas ────────────────────────────────────────────────────────

class AttachmentPresignResponse(BaseModel):
    """Returned after requesting a presigned upload URL."""
    attachment_id: int
    upload_url: str
    s3_key: str

    model_config = {"from_attributes": True}


class AttachmentResponse(BaseModel):
    """Full attachment representation with a download URL."""
    id: int
    ticket_id: int
    uploaded_by: int | None = None
    uploaded_by_username: str | None = None
    filename: str
    content_type: str
    file_size: int | None = None
    download_url: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
