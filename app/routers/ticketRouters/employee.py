from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.limiter import limiter
from app.dependencies.user import get_current_user
from app.dependencies.db import get_db
from app.models.userModel import User
from app.schemas.ticketSchema import TicketCreate, TicketResponse, TicketUpdate
from app.services.ticketService.employee import ticket_service_employee

router = APIRouter(prefix="/tickets/employee", tags=["Employee Tickets"])


@router.post("/create", status_code=201, response_model=TicketResponse)
@limiter.limit("20/minute")
def create_ticket(
    request: Request,
    ticket: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ticket_service_employee.create_ticket(ticket, db, current_user)


@router.get("/all", response_model=list[TicketResponse])
@limiter.limit("30/minute")
def get_my_tickets(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 10,
    offset: int = 0,
):
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
    return ticket_service_employee.get_created_tickets(db, current_user, limit, offset)


@router.get("/assigned-to-me", response_model=list[TicketResponse])
@limiter.limit("30/minute")
def get_assigned_tickets(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 10,
    offset: int = 0,
):
    return ticket_service_employee.get_assigned_tickets(db, current_user, limit, offset)


@router.get("/get/{id}", response_model=TicketResponse)
@limiter.limit("30/minute")
def get_ticket(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ticket_service_employee.get_ticket(id, db, current_user)


@router.patch("/{id}/update", response_model=TicketResponse)
@limiter.limit("20/minute")
def update_ticket(
    request: Request,
    id: int,
    ticket: TicketUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ticket_service_employee.update_ticket(id, ticket, db, current_user)