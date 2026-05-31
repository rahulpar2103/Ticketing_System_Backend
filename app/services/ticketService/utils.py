from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, asc, desc
from app.models.ticketModel import Ticket, TicketStatus, Priority
from app.schemas.ticketSchema import TicketResponse
from app.core.exceptions import ValidationException


def _build_response(ticket: Ticket) -> TicketResponse:
    return TicketResponse(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        priority=ticket.priority,
        created_by=ticket.created_by,
        created_by_username=ticket.created_by_user.username if ticket.created_by_user else None,
        assigned_to=ticket.assigned_to,
        assigned_to_username=ticket.assigned_user.username if ticket.assigned_user else None,
        team_id=ticket.team_id,
        team_name=ticket.team.name if ticket.team else None,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        due_at=ticket.due_at,
        sla_breached=ticket.sla_breached,
        comment_count=ticket.comment_count if hasattr(ticket, 'comment_count') else 0,
        attachment_count=ticket.attachment_count if hasattr(ticket, 'attachment_count') else 0,
        is_active=ticket.is_active,
    )


def _load_ticket(db: Session, ticket_id: int):
    return (
        db.query(Ticket)
        .options(
            joinedload(Ticket.assigned_user),
            joinedload(Ticket.created_by_user),
            joinedload(Ticket.team),
        )
        .filter(Ticket.id == ticket_id, Ticket.is_active == True)
        .first()
    )


def _load_tickets(query):
    return query.options(
        joinedload(Ticket.assigned_user),
        joinedload(Ticket.created_by_user),
        joinedload(Ticket.team),
    )


# Ticket search, filter, and sorting utilities

# Fields allowed for sorting on tickets
TICKET_SORTABLE_FIELDS = {
    "created_at": Ticket.created_at,
    "updated_at": Ticket.updated_at,
    "priority": Ticket.priority,
    "status": Ticket.status,
    "title": Ticket.title,
}


def apply_ticket_filters(query, search: str | None, status: str | None, priority: str | None):
    """Apply search and filter predicates to a ticket query."""
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(Ticket.title.ilike(pattern), Ticket.description.ilike(pattern))
        )

    if status:
        status_values = [s.strip() for s in status.split(",") if s.strip()]
        valid_statuses = []
        for s in status_values:
            try:
                valid_statuses.append(TicketStatus(s))
            except ValueError:
                raise ValidationException(
                    f"Invalid status '{s}'. Allowed: {[st.value for st in TicketStatus]}"
                )
        if valid_statuses:
            query = query.filter(Ticket.status.in_(valid_statuses))

    if priority:
        priority_values = [p.strip() for p in priority.split(",") if p.strip()]
        valid_priorities = []
        for p in priority_values:
            try:
                valid_priorities.append(Priority(p))
            except ValueError:
                raise ValidationException(
                    f"Invalid priority '{p}'. Allowed: {[pr.value for pr in Priority]}"
                )
        if valid_priorities:
            query = query.filter(Ticket.priority.in_(valid_priorities))

    return query


def apply_ticket_sorting(query, sort_by: str = "created_at", order: str = "desc"):
    """Apply sorting to a ticket query."""
    column = TICKET_SORTABLE_FIELDS.get(sort_by)
    if column is None:
        raise ValidationException(
            f"Invalid sort_by '{sort_by}'. Allowed: {list(TICKET_SORTABLE_FIELDS.keys())}"
        )
    if order not in ("asc", "desc"):
        raise ValidationException("Invalid order. Allowed: 'asc', 'desc'")

    order_func = asc if order == "asc" else desc
    return query.order_by(order_func(column))


def paginate_tickets(query, limit: int, offset: int):
    """Execute a ticket query and return items + metadata dict."""
    from sqlalchemy import func

    # Leverage a window function to retrieve the total matching rows and items in a single query
    count_query = query.add_columns(func.count().over().label("total_count"))
    db_results = _load_tickets(count_query).limit(limit).offset(offset).all()

    if db_results:
        tickets = [row[0] for row in db_results]
        total = db_results[0][1]
    else:
        tickets = []
        total = 0

    responses = [_build_response(t) for t in tickets]
    return {
        "items": responses,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
    }
