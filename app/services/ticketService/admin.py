
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


class AdminTicketService:
    @staticmethod
    def create_ticket(ticket: TicketCreate, db: Session, user: User):
        pass
    
    @staticmethod
    def get_all_tickets(db: Session, user: User, limit: int, offset: int):
        pass
    
    @staticmethod
    def get_ticket(id: int, db: Session, user: User):
        pass
    
    @staticmethod
    def get_assigned_tickets(db: Session, user: User, limit: int, offset: int):
        pass    
    
    @staticmethod
    def get_created_tickets(db: Session, user: User, limit: int, offset: int):
        pass
    
    @staticmethod
    def get_team_tickets(team_id: int, db: Session, user: User):
        pass
    
    @staticmethod
    def update_ticket(id: int, ticket: TicketUpdate, db: Session, user: User):
        pass

ticket_service_admin = AdminTicketService()