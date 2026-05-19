from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session
from app.core.limiter import limiter
from app.dependencies.db import get_db
from app.dependencies.user import get_current_user
from app.models.userModel import User, UserRole
from app.schemas.ticketSchema import TicketCreate, TicketUpdate, TicketResponse
from app.schemas.pagination import PaginatedResponse
from app.schemas.auditSchema import AuditLogResponse
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




@router.get("", response_model=PaginatedResponse[TicketResponse])
@limiter.limit("30/minute")
def get_tickets(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, description="Search in title and description"),
    status: str | None = Query(None, description="Filter by status (comma-separated, e.g. open,in_progress)"),
    priority: str | None = Query(None, description="Filter by priority (comma-separated, e.g. high,urgent)"),
    sort_by: str = Query("created_at", description="Sort field: created_at, updated_at, priority, status, title"),
    order: str = Query("desc", description="Sort order: asc or desc"),
):
    """
    Get tickets visible to the current user with search, filter, and sort.
    - Admin: all tickets
    - Agent: tickets they created, are assigned to, or belong to their team
    - Employee: tickets they created or are assigned to
    """
    role = current_user.role
    if role == UserRole.admin:
        return ticket_service_admin.get_all_tickets(
            db, current_user, limit, offset, search, status, priority, sort_by, order
        )
    elif role == UserRole.agent:
        return ticket_service_agent.get_my_tickets(
            db, current_user, limit, offset, search, status, priority, sort_by, order
        )
    else:
        return ticket_service_employee.get_my_tickets(
            db, current_user, limit, offset, search, status, priority, sort_by, order
        )


@router.get("/created-by-me", response_model=PaginatedResponse[TicketResponse])
@limiter.limit("30/minute")
def get_created_tickets(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None),
    status: str | None = Query(None),
    priority: str | None = Query(None),
    sort_by: str = Query("created_at"),
    order: str = Query("desc"),
):
    """Get tickets created by the current user."""
    service = _get_ticket_service(current_user.role)
    return service.get_created_tickets(
        db, current_user, limit, offset, search, status, priority, sort_by, order
    )


@router.get("/assigned-to-me", response_model=PaginatedResponse[TicketResponse])
@limiter.limit("30/minute")
def get_assigned_tickets(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None),
    status: str | None = Query(None),
    priority: str | None = Query(None),
    sort_by: str = Query("created_at"),
    order: str = Query("desc"),
):
    """Get tickets assigned to the current user."""
    service = _get_ticket_service(current_user.role)
    return service.get_assigned_tickets(
        db, current_user, limit, offset, search, status, priority, sort_by, order
    )


@router.get("/team/{team_id}", response_model=PaginatedResponse[TicketResponse])
@limiter.limit("30/minute")
def get_team_tickets(
    request: Request,
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None),
    status: str | None = Query(None),
    priority: str | None = Query(None),
    sort_by: str = Query("created_at"),
    order: str = Query("desc"),
):
    """Get tickets for a specific team. Admin can specify any team; agent gets own team."""
    role = current_user.role
    if role == UserRole.admin:
        return ticket_service_admin.get_team_tickets(
            team_id, db, current_user, limit, offset, search, status, priority, sort_by, order
        )
    elif role == UserRole.agent:
        return ticket_service_agent.get_team_tickets(
            db, current_user, limit, offset, search, status, priority, sort_by, order
        )
    else:
        from app.core.exceptions import PermissionDeniedException
        raise PermissionDeniedException("Employees cannot view team tickets")


@router.get("/user/{user_id}/assigned", response_model=PaginatedResponse[TicketResponse])
@limiter.limit("30/minute")
def get_tickets_assigned_to_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None),
    status: str | None = Query(None),
    priority: str | None = Query(None),
    sort_by: str = Query("created_at"),
    order: str = Query("desc"),
):
    """Get tickets assigned to a specific user. Admin only."""
    return ticket_service_admin.get_tickets_assigned_to_user(
        user_id, db, current_user, limit, offset, search, status, priority, sort_by, order
    )


@router.get("/stats", response_model=dict)
@limiter.limit("30/minute")
def get_ticket_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    team_id: int | None = Query(None, description="Optional: filter stats by team ID"),
):
    """Get ticket statistics (counts by status and priority). Admin only."""
    return ticket_service_admin.get_ticket_stats(db, current_user, team_id)


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


@router.get("/{ticket_id}/history", response_model=PaginatedResponse[AuditLogResponse])
@limiter.limit("30/minute")
def get_ticket_history(
    request: Request,
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get the audit history of a specific ticket."""
    from app.services.auditService import get_ticket_audit_logs
    return get_ticket_audit_logs(ticket_id, db, current_user, limit, offset)




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




@router.delete("/{ticket_id}", response_model=dict)
@limiter.limit("20/minute")
def delete_ticket(
    request: Request,
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soft-delete a ticket. Behavior varies by role:
    - Admin: can delete any ticket
    - Agent: can delete accessible tickets (own team / created / assigned)
    - Employee: can only delete own open tickets
    """
    service = _get_ticket_service(current_user.role)
    return service.delete_ticket(ticket_id, db, current_user)




@router.patch("/{ticket_id}/reactivate", response_model=dict)
@limiter.limit("20/minute")
def reactivate_ticket(
    request: Request,
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-enable a soft-deleted ticket. Admin only."""
    return ticket_service_admin.reactivate_ticket(ticket_id, db, current_user)
