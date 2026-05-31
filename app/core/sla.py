from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.ticketModel import Ticket, TicketStatus, Priority

SLA_TIERS = {
    Priority.low: timedelta(hours=48),
    Priority.medium: timedelta(hours=24),
    Priority.high: timedelta(hours=12),
    Priority.urgent: timedelta(hours=4)
}

def calculate_due_at(created_at: datetime, priority: Priority) -> datetime:
    """Calculate the due deadline based on creation time and ticket priority."""
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return created_at + SLA_TIERS[priority]

def update_expired_slas(db: Session):
    """
    Lazy SLA breach updater.
    Finds all unresolved (open or in_progress) active tickets
    whose due_at is in the past and marks them as breached.
    """
    now = datetime.now(timezone.utc)
    db.query(Ticket).filter(
        Ticket.is_active == True,
        Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress]),
        Ticket.due_at < now,
        Ticket.sla_breached == False
    ).update({Ticket.sla_breached: True}, synchronize_session=False)
    db.commit()
