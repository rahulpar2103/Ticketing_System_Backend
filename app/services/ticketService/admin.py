
# pyrefly: ignore [missing-import]
from app.models.ticketModel import Ticket
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from app.models.userModel import User
# pyrefly: ignore [missing-import]
from app.schemas.ticketSchema import TicketCreate, TicketUpdate
# pyrefly: ignore [missing-import]
from app.core.exceptions import (
    NotFoundException,
    PermissionDeniedException,
    UnauthorizedException,
    AlreadyExistsException,
    InvalidCredentialsException,
    SessionException,
    MissingCredentialException,
    ValidationException
)
from app.db.redis import redis_client


class AdminTicketService:
    @staticmethod
    def create_ticket(ticket: TicketCreate, db: Session, current_user: User):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Not allowed to access this endpoint") 
        new_ticket = Ticket(
            title=ticket.title,
            description=ticket.description,
            priority=ticket.priority,
            assigned_to=ticket.assigned_to,
            created_by=current_user.id
        )
        
        db.add(new_ticket)
        db.commit()
        db.refresh(new_ticket)
        return new_ticket
    
    @staticmethod
    def get_all_tickets(db: Session, current_user: User, limit: int, offset: int):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Not allowed to access this endpoint") 
        cache_key = f"tickets:all:{limit}:{offset}"
        cached_tickets = redis_client.get(cache_key)
        if cached_tickets:
            return cached_tickets
        
        tickets = db.query(Ticket).limit(limit).offset(offset).all()
        json_tickets = [t.model_dump() for t in tickets]
        redis_client.setex(cache_key, 60*60*24, json_tickets)
        return tickets
    
    @staticmethod
    def get_ticket(id: int, db: Session, current_user: User):
        pass
    
    @staticmethod
    def get_assigned_tickets(db: Session, current_user: User, limit: int, offset: int):
        pass    
    
    @staticmethod
    def get_created_tickets(db: Session, current_user: User, limit: int, offset: int):
        pass
    
    @staticmethod
    def get_team_tickets(team_id: int, db: Session, current_user: User):
        pass
    
    @staticmethod
    def update_ticket(id: int, ticket: TicketUpdate, db: Session, current_user: User):
        pass

ticket_service_admin = AdminTicketService()