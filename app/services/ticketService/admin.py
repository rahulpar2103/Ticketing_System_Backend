
# pyrefly: ignore [missing-import]
from app.db.redis import delete_by_prefix
from app.models.ticketModel import Priority
from app.models.ticketModel import TicketStatus
from app.models.teamModel import Team
from app.schemas.ticketSchema import TicketResponse
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
import json

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
        cached = redis_client.get(cache_key)
        if cached:
            return [TicketResponse.model_validate(t) for t in json.loads(cached)]
        tickets = db.query(Ticket).limit(limit).offset(offset).all()
        serialized = [TicketResponse.model_validate(t).model_dump(mode="json") for t in tickets]
        redis_client.setex(cache_key, 60 * 60 * 24, json.dumps(serialized))
        return [TicketResponse.model_validate(t) for t in tickets]

    @staticmethod
    def get_ticket(id: int, db: Session, current_user: User):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Not allowed to access this endpoint")
        cache_key = f"ticket:{id}"
        cached = redis_client.get(cache_key)
        if cached:
            return TicketResponse.model_validate(json.loads(cached))
        ticket = db.query(Ticket).filter(Ticket.id == id).first()
        if not ticket:
            raise NotFoundException(f"Ticket {id} not found")
        redis_client.setex(cache_key, 60 * 60 * 24, json.dumps(TicketResponse.model_validate(ticket).model_dump(mode="json")))
        return TicketResponse.model_validate(ticket)    
    
    @staticmethod
    def get_assigned_tickets(db: Session, current_user: User, limit: int, offset: int):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Not allowed to access this endpoint")
        cache_key = f"tickets:assigned:{current_user.id}:{limit}:{offset}"
        cached = redis_client.get(cache_key)
        if cached:
            return [TicketResponse.model_validate(t) for t in json.loads(cached)]
        tickets = db.query(Ticket).filter(Ticket.assigned_to == current_user.id).limit(limit).offset(offset).all()
        serialized = [TicketResponse.model_validate(t).model_dump(mode="json") for t in tickets]
        redis_client.setex(cache_key, 60 * 60 * 24, json.dumps(serialized))
        return [TicketResponse.model_validate(t) for t in tickets]    
    
    @staticmethod
    def get_created_tickets(db: Session, current_user: User, limit: int, offset: int):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Not allowed to access this endpoint")
        cache_key = f"tickets:created:{current_user.id}:{limit}:{offset}"
        cached = redis_client.get(cache_key)
        if cached:
            return [TicketResponse.model_validate(t) for t in json.loads(cached)]
        tickets = db.query(Ticket).filter(Ticket.created_by == current_user.id).limit(limit).offset(offset).all()
        serialized = [TicketResponse.model_validate(t).model_dump(mode="json") for t in tickets]
        redis_client.setex(cache_key, 60 * 60 * 24, json.dumps(serialized))
        return [TicketResponse.model_validate(t) for t in tickets]    
    
    @staticmethod
    def get_team_tickets(team_id: int, db: Session, current_user: User, limit: int, offset: int):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Not allowed to access this endpoint")
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise NotFoundException(f"Team {team_id} not found")
        cache_key = f"tickets:team:{team_id}:{limit}:{offset}"
        cached = redis_client.get(cache_key)
        if cached:
            return [TicketResponse.model_validate(t) for t in json.loads(cached)]
        tickets = db.query(Ticket).filter(Ticket.assigned_to.in_([t.id for t in db.query(User).filter(User.team_id == team_id).all()])).limit(limit).offset(offset).all()
        serialized = [TicketResponse.model_validate(t).model_dump(mode="json") for t in tickets]
        redis_client.setex(cache_key, 60 * 60 * 24, json.dumps(serialized))
        return [TicketResponse.model_validate(t) for t in tickets]
    
    @staticmethod
    def get_tickets_assigned_to_user(user_id: int, db: Session, current_user: User, limit: int, offset: int):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Not allowed to access this endpoint")
        cache_key = f"tickets:assigned:{user_id}:{limit}:{offset}"
        cached = redis_client.get(cache_key)
        if cached:
            return [TicketResponse.model_validate(t) for t in json.loads(cached)]
        tickets = db.query(Ticket).filter(Ticket.assigned_to == user_id).limit(limit).offset(offset).all()
        serialized = [TicketResponse.model_validate(t).model_dump(mode="json") for t in tickets]
        redis_client.setex(cache_key, 60 * 60 * 24, json.dumps(serialized))
        return [TicketResponse.model_validate(t) for t in tickets]    

    @staticmethod
    def update_ticket(id: int, ticket_update: TicketUpdate, db: Session, current_user: User):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Not allowed to access this endpoint")
        ticket_to_update = db.query(Ticket).filter(Ticket.id == id).first()
        if not ticket_to_update:
            raise NotFoundException(f"Ticket {id} not found")
        if ticket_update.title is not None:
            ticket_to_update.title = ticket_update.title
        if ticket_update.description is not None:
            ticket_to_update.description = ticket_update.description
        if ticket_update.status is not None:
            ticket_to_update.status = ticket_update.status
        if ticket_update.assigned_to is not None:
            user = db.query(User).filter(User.id == ticket_update.assigned_to).first()
            if not user:
                raise NotFoundException(f"User {ticket_update.assigned_to} not found")
            ticket_to_update.assigned_to = ticket_update.assigned_to
        if ticket_update.priority is not None:
            ticket_to_update.priority = ticket_update.priority

        db.commit()
        db.refresh(ticket_to_update)

        redis_client.delete(f"ticket:{id}")
        delete_by_prefix("tickets:all:")
        delete_by_prefix("tickets:assigned:")
        delete_by_prefix("tickets:team:")

        return TicketResponse.model_validate(ticket_to_update)
    
ticket_service_admin = AdminTicketService()