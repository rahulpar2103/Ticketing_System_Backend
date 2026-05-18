from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.limiter import limiter
from app.dependencies.db import get_db
from app.dependencies.user import get_current_user
from app.models.userModel import User, UserRole
from app.schemas.ticketSchema import TicketCreate, TicketUpdate, TicketResponse
from app.services.ticketService.admin import ticket_service_admin
from app.services.ticketService.agent import ticket_service_agent
from app.services.ticketService.employee import ticket_service_employee

router = APIRouter(prefix="/tickets", tags=["Tickets"])


def _get_ticket_service(role: UserRole):
    """Return the appropriate ticket service based on the user's role."""
    services = {
        UserRole.admin: ticket_service_admin,
        UserRole.agent: ticket_service_agent,
        UserRole.employee: ticket_service_employee,
    }
    return services[role]


# ------------------------------------------------------------------ #
# CREATE                                                               #
# ------------------------------------------------------------------ #

@router.post("", status_code=201, response_model=TicketResponse)
@limiter.limit("30/minute")
def create_ticket(
    request: Request,
    ticket: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new ticket. Behavior varies by role."""
    service = _get_ticket_service(current_user.role)
    return service.create_ticket(ticket, db, current_user)


# ------------------------------------------------------------------ #
# READ                                                                 #
# ------------------------------------------------------------------ #

@router.get("", response_model=list[TicketResponse])
@limiter.limit("30/minute")
def get_tickets(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 10,
    offset: int = 0,
):
    """
    Get tickets visible to the current user.
    - Admin: all tickets
    - Agent: tickets they created, are assigned to, or belong to their team
    - Employee: tickets they created or are assigned to
    """
    role = current_user.role
    if role == UserRole.admin:
        return ticket_service_admin.get_all_tickets(db, current_user, limit, offset)
    elif role == UserRole.agent:
        return ticket_service_agent.get_my_tickets(db, current_user, limit, offset)
    else:
        return ticket_service_employee.get_my_tickets(db, current_user, limit, offset)


@router.get("/created-by-me", response_model=list[TicketResponse])
@limiter.limit("30/minute")
def get_created_tickets(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 10,
    offset: int = 0,
):
    """Get tickets created by the current user."""
    service = _get_ticket_service(current_user.role)
    return service.get_created_tickets(db, current_user, limit, offset)


@router.get("/assigned-to-me", response_model=list[TicketResponse])
@limiter.limit("30/minute")
def get_assigned_tickets(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 10,
    offset: int = 0,
):
    """Get tickets assigned to the current user."""
    service = _get_ticket_service(current_user.role)
    return service.get_assigned_tickets(db, current_user, limit, offset)


@router.get("/team/{team_id}", response_model=list[TicketResponse])
@limiter.limit("30/minute")
def get_team_tickets(
    request: Request,
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 10,
    offset: int = 0,
):
    """Get tickets for a specific team. Admin can specify any team; agent gets own team."""
    role = current_user.role
    if role == UserRole.admin:
        return ticket_service_admin.get_team_tickets(team_id, db, current_user, limit, offset)
    elif role == UserRole.agent:
        return ticket_service_agent.get_team_tickets(db, current_user, limit, offset)
    else:
        from app.core.exceptions import PermissionDeniedException
        raise PermissionDeniedException("Employees cannot view team tickets")


@router.get("/user/{user_id}/assigned", response_model=list[TicketResponse])
@limiter.limit("30/minute")
def get_tickets_assigned_to_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 10,
    offset: int = 0,
):
    """Get tickets assigned to a specific user. Admin only."""
    return ticket_service_admin.get_tickets_assigned_to_user(user_id, db, current_user, limit, offset)


@router.get("/{ticket_id}", response_model=TicketResponse)
@limiter.limit("30/minute")
def get_ticket(
    request: Request,
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single ticket by ID. Behavior varies by role."""
    service = _get_ticket_service(current_user.role)
    return service.get_ticket(ticket_id, db, current_user)


# ------------------------------------------------------------------ #
# UPDATE                                                               #
# ------------------------------------------------------------------ #

@router.patch("/{ticket_id}", response_model=TicketResponse)
@limiter.limit("20/minute")
def update_ticket(
    request: Request,
    ticket_id: int,
    ticket: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a ticket. Behavior varies by role."""
    service = _get_ticket_service(current_user.role)
    return service.update_ticket(ticket_id, ticket, db, current_user)
