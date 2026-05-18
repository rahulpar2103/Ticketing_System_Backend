import json
from sqlalchemy.orm import Session, joinedload
from app.models.ticketModel import Ticket
from app.schemas.ticketSchema import TicketResponse


def _build_response(ticket: Ticket) -> TicketResponse:
    return TicketResponse(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        priority=ticket.priority,
        created_by=ticket.created_by,
        assigned_to=ticket.assigned_to,
        assigned_to_username=ticket.assigned_user.username if ticket.assigned_user else None,
        team_id=ticket.team_id,
        team_name=ticket.team.name if ticket.team else None,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
    )

def _load_ticket(db: Session, ticket_id: int):
    return (
        db.query(Ticket)
        .options(joinedload(Ticket.assigned_user), joinedload(Ticket.team))
        .filter(Ticket.id == ticket_id, Ticket.is_active == True)
        .first()
    )

def _load_tickets(query):
    return query.options(joinedload(Ticket.assigned_user), joinedload(Ticket.team))

