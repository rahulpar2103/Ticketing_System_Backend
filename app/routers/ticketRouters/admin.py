# pyrefly: ignore [missing-import]
from app.services.ticketService.admin import AdminTicketService
from app.models.ticketModel import TicketStatus
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends
# pyrefly: ignore [missing-import]
from app.dependencies.user import get_current_user, get_db
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from app.models.userModel import User
# pyrefly: ignore [missing-import]
from app.schemas.ticketSchema import TicketCreate, TicketResponse, TicketUpdate
# pyrefly: ignore [missing-import]
from app.services.ticketService.admin import ticket_service_admin


router = APIRouter(prefix="/tickets/admin",tags=["Admin Tickets"])


@router.post("/create", status_code=201, response_model=TicketResponse)
def create_ticket(ticket: TicketCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ticket_service_admin.create_ticket(ticket, db, current_user)

@router.get("/all")
def get_all_tickets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), limit: int=10, offset: int=0):
    return ticket_service_admin.get_all_tickets(db, current_user, limit, offset)

@router.get("/get/{id}")
def get_ticket(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ticket_service_admin.get_ticket(id, db, current_user)

@router.get("/assigned-to-me")
def get_assigned_tickets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), limit: int=10, offset: int=0):
    return ticket_service_admin.get_assigned_tickets(db, current_user, limit, offset)

@router.get("/created-by-me")
def get_created_tickets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), limit: int=10, offset: int=0):
    return ticket_service_admin.get_created_tickets(db, current_user, limit, offset)

@router.get("/team-tickets/{team_id}")
def get_team_tickets(team_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ticket_service_admin.get_team_tickets(team_id, db, current_user)

@router.patch('/{id}/update')
def update_ticket(id: int, ticket: TicketUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ticket_service_admin.update_ticket(id, ticket, db, current_user)

