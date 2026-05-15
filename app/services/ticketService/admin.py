import json
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session, joinedload
from app.db.redis import delete_by_prefix, redis_client
from app.models.ticketModel import Ticket
from app.models.teamModel import Team
from app.models.userModel import User
from app.schemas.ticketSchema import TicketCreate, TicketUpdate, TicketResponse
from app.core.exceptions import NotFoundException, PermissionDeniedException


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
    )

def _load_ticket(db: Session, ticket_id: int):
    """Single ticket query with relationships eager-loaded."""
    return (
        db.query(Ticket)
        .options(joinedload(Ticket.assigned_user), joinedload(Ticket.team))
        .filter(Ticket.id == ticket_id)
        .first()
    )

def _load_tickets(query):
    """Apply eager loading to any ticket query."""
    return query.options(joinedload(Ticket.assigned_user), joinedload(Ticket.team))


class AdminTicketService:

    @staticmethod
    def create_ticket(ticket: TicketCreate, db: Session, current_user: User):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("Not allowed to access this endpoint")

        if ticket.assigned_to is not None:
            user = db.query(User).filter(User.id == ticket.assigned_to).first()
            if not user:
                raise NotFoundException(f"User {ticket.assigned_to} not found")

        if ticket.team_id is not None:
            team = db.query(Team).filter(Team.id == ticket.team_id).first()
            if not team:
                raise NotFoundException(f"Team {ticket.team_id} not found")

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

        # reload with relationships
        new_ticket = _load_ticket(db, new_ticket.id)
        delete_by_prefix("tickets:all:")
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

        if ticket_update.assigned_to is not None:
            user = db.query(User).filter(User.id == ticket_update.assigned_to).first()
            if not user:
                raise NotFoundException(f"User {ticket_update.assigned_to} not found")
            ticket.assigned_to = ticket_update.assigned_to

        if ticket_update.team_id is not None:
            if ticket_update.team_id == 0:
                ticket.team_id = None
            else:
                team = db.query(Team).filter(Team.id == ticket_update.team_id).first()
                if not team:
                    raise NotFoundException(f"Team {ticket_update.team_id} not found")
                ticket.team_id = ticket_update.team_id
                ticket.assigned_to = None

        db.commit()

        ticket = _load_ticket(db, id)
        redis_client.delete(f"ticket:{id}")
        delete_by_prefix("tickets:all:")
        delete_by_prefix("tickets:assigned:")
        delete_by_prefix("tickets:team:")
        delete_by_prefix("tickets:created:")

        return _build_response(ticket)


ticket_service_admin = AdminTicketService()