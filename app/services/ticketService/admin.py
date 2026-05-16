from app.core.exceptions import ValidationException
import json
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from app.db.redis import delete_by_prefix, redis_client
from app.models.ticketModel import Ticket
from app.models.teamModel import Team
from app.models.userModel import User
from app.schemas.ticketSchema import TicketCreate, TicketUpdate, TicketResponse
from app.core.exceptions import NotFoundException, PermissionDeniedException, ValidationException
from app.services.ticketService.utils import _build_response, _load_ticket, _load_tickets


class AdminTicketService:

    @staticmethod
    def create_ticket(ticket: TicketCreate, db: Session, current_user: User):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Not allowed to access this endpoint")

        # Normalize sentinel values
        if ticket.assigned_to == -1:
            ticket.assigned_to = None
        if ticket.team_id == 0:
            ticket.team_id = None

        assigned_user = None
        if ticket.assigned_to is not None:
            assigned_user = db.query(User).filter(User.id == ticket.assigned_to).first()
            if not assigned_user:
                raise NotFoundException(f"User {ticket.assigned_to} not found")

        if ticket.team_id is not None:
            team = db.query(Team).filter(Team.id == ticket.team_id).first()
            if not team:
                raise NotFoundException(f"Team {ticket.team_id} not found")

            if assigned_user is not None and assigned_user.team_id != ticket.team_id:
                raise ValidationException(
                    f"User {assigned_user.username} does not belong to team {ticket.team_id}"
                )
        elif assigned_user is not None:
            ticket.team_id = assigned_user.team_id  

        new_ticket = Ticket(
            title=ticket.title,
            description=ticket.description,
            priority=ticket.priority,
            assigned_to=ticket.assigned_to,
            team_id=ticket.team_id,
            created_by=current_user.id,
        )
        db.add(new_ticket)
        db.commit()

        new_ticket = _load_ticket(db, new_ticket.id)
        delete_by_prefix("tickets:")
        return _build_response(new_ticket)
    
    @staticmethod
    def get_all_tickets(db: Session, current_user: User, limit: int, offset: int):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Not allowed to access this endpoint")
        cache_key = f"tickets:all:{limit}:{offset}"
        cached = redis_client.get(cache_key)
        if cached:
            return [TicketResponse.model_validate(t) for t in json.loads(cached)]
        tickets = _load_tickets(db.query(Ticket)).limit(limit).offset(offset).all()
        responses = [_build_response(t) for t in tickets]
        redis_client.setex(cache_key, 60 * 60, json.dumps([r.model_dump(mode="json") for r in responses]))
        return responses

    @staticmethod
    def get_ticket(id: int, db: Session, current_user: User):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Not allowed to access this endpoint")
        cache_key = f"ticket:{id}"
        cached = redis_client.get(cache_key)
        if cached:
            return TicketResponse.model_validate(json.loads(cached))
        ticket = _load_ticket(db, id)
        if not ticket:
            raise NotFoundException(f"Ticket {id} not found")
        response = _build_response(ticket)
        redis_client.setex(cache_key, 60 * 60, json.dumps(response.model_dump(mode="json")))
        return response

    @staticmethod
    def get_assigned_tickets(db: Session, current_user: User, limit: int, offset: int):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Not allowed to access this endpoint")
        cache_key = f"tickets:assigned:{current_user.id}:{limit}:{offset}"
        cached = redis_client.get(cache_key)
        if cached:
            return [TicketResponse.model_validate(t) for t in json.loads(cached)]
        tickets = _load_tickets(
            db.query(Ticket).filter(Ticket.assigned_to == current_user.id)
        ).limit(limit).offset(offset).all()
        responses = [_build_response(t) for t in tickets]
        redis_client.setex(cache_key, 60 * 60, json.dumps([r.model_dump(mode="json") for r in responses]))
        return responses

    @staticmethod
    def get_created_tickets(db: Session, current_user: User, limit: int, offset: int):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Not allowed to access this endpoint")
        cache_key = f"tickets:created:{current_user.id}:{limit}:{offset}"
        cached = redis_client.get(cache_key)
        if cached:
            return [TicketResponse.model_validate(t) for t in json.loads(cached)]
        tickets = _load_tickets(
            db.query(Ticket).filter(Ticket.created_by == current_user.id)
        ).limit(limit).offset(offset).all()
        responses = [_build_response(t) for t in tickets]
        redis_client.setex(cache_key, 60 * 60, json.dumps([r.model_dump(mode="json") for r in responses]))
        return responses

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
        tickets = _load_tickets(
            db.query(Ticket).filter(Ticket.team_id == team_id)
        ).limit(limit).offset(offset).all()
        responses = [_build_response(t) for t in tickets]
        redis_client.setex(cache_key, 60 * 60, json.dumps([r.model_dump(mode="json") for r in responses]))
        return responses

    @staticmethod
    def get_tickets_assigned_to_user(user_id: int, db: Session, current_user: User, limit: int, offset: int):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Not allowed to access this endpoint")
        cache_key = f"tickets:assigned:{user_id}:{limit}:{offset}"
        cached = redis_client.get(cache_key)
        if cached:
            return [TicketResponse.model_validate(t) for t in json.loads(cached)]
        tickets = _load_tickets(
            db.query(Ticket).filter(Ticket.assigned_to == user_id)
        ).limit(limit).offset(offset).all()
        responses = [_build_response(t) for t in tickets]
        redis_client.setex(cache_key, 60 * 60, json.dumps([r.model_dump(mode="json") for r in responses]))
        return responses

    @staticmethod
    def update_ticket(id: int, ticket_update: TicketUpdate, db: Session, current_user: User):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Not allowed to access this endpoint")

        ticket = db.query(Ticket).filter(Ticket.id == id).first()
        if not ticket:
            raise NotFoundException(f"Ticket {id} not found")

        if ticket_update.title is not None:
            ticket.title = ticket_update.title
        if ticket_update.description is not None:
            ticket.description = ticket_update.description
        if ticket_update.status is not None:
            ticket.status = ticket_update.status
        if ticket_update.priority is not None:
            ticket.priority = ticket_update.priority

        unassign_user = ticket_update.assigned_to == -1
        unassign_team = ticket_update.team_id == 0

        if unassign_user:
            ticket_update.assigned_to = None
        if unassign_team:
            ticket_update.team_id = None

        new_assignee = None
        if ticket_update.assigned_to is not None:
            new_assignee = db.query(User).filter(User.id == ticket_update.assigned_to).first()
            if not new_assignee:
                raise NotFoundException(f"User {ticket_update.assigned_to} not found")

        new_team = None
        if ticket_update.team_id is not None:
            new_team = db.query(Team).filter(Team.id == ticket_update.team_id).first()
            if not new_team:
                raise NotFoundException(f"Team {ticket_update.team_id} not found")

        if unassign_team:
            ticket.team_id = None
            ticket.assigned_to = None

        elif new_team is not None and new_assignee is not None:
            if new_assignee.team_id != new_team.id:
                raise ValidationException(
                    f"User {new_assignee.username} does not belong to team {new_team.id}"
                )
            ticket.team_id = new_team.id
            ticket.assigned_to = new_assignee.id

        elif new_team is not None:
            ticket.team_id = new_team.id
            if ticket.assigned_to is not None:
                current_assignee = db.query(User).filter(User.id == ticket.assigned_to).first()
                if current_assignee and current_assignee.team_id != new_team.id:
                    ticket.assigned_to = None

        elif new_assignee is not None:
            ticket.assigned_to = new_assignee.id
            if ticket.team_id is None:
                ticket.team_id = new_assignee.team_id  
            elif new_assignee.team_id != ticket.team_id:
                raise ValidationException(
                    f"User {new_assignee.username} does not belong to the ticket's current team. "
                    f"Update team_id explicitly if you intend to transfer."
                )

        if unassign_user and not unassign_team:
            ticket.assigned_to = None

        db.commit()

        ticket = _load_ticket(db, id)
        redis_client.delete(f"ticket:{id}")
        delete_by_prefix("tickets:")
        return _build_response(ticket)
ticket_service_admin = AdminTicketService()