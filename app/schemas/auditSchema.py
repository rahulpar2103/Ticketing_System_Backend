from pydantic import BaseModel
from datetime import datetime
from typing import Any

class AuditLogResponse(BaseModel):
    id: int
    ticket_id: int
    user_id: int | None
    username: str | None = None
    action: str
    changes: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
