import json
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from sqlalchemy import or_
from app.db.redis import redis_client, delete_by_prefix
from app.models.ticketModel import Ticket, TicketStatus
from app.models.teamModel import Team
from app.models.userModel import User
from app.schemas.ticketSchema import TicketCreate, TicketUpdate, TicketResponse
from app.core.exceptions import NotFoundException, PermissionDeniedException, ValidationException
from app.services.ticketService.utils import _build_response, _load_ticket, _load_tickets

# Valid status transitions for agents (and admins)
VALID_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.open:        {TicketStatus.in_progress},
    TicketStatus.in_progress: {TicketStatus.resolved},
    TicketStatus.resolved:    {TicketStatus.closed},
    TicketStatus.closed:      set(),
}


class AgentTicketService:

    @staticmethod
    def _require_agent(current_user: User):
        if current_user.role.value != "agent":
            raise PermissionDeniedException("Not allowed to access this endpoint")

    @staticmethod
    def _is_accessible(ticket: Ticket, current_user: User) -> bool:
        """Ticket is accessible if the agent created it, is assigned to it, or it belongs to their team."""
        return (
            ticket.created_by == current_user.id
            or ticket.assigned_to == current_user.id
            or (current_user.team_id is not None and ticket.team_id == current_user.team_id)
        )

    @staticmethod
    def _is_team_ticket(ticket: Ticket, current_user: User) -> bool:
        return current_user.team_id is not None and ticket.team_id == current_user.team_id

    # ------------------------------------------------------------------ #
    # CREATE                                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def create_ticket(ticket: TicketCreate, db: Session, current_user: User):
        AgentTicketService._require_agent(current_user)

        if ticket.assigned_to is not None:
            if not db.query(User).filter(User.id == ticket.assigned_to).first():
                raise NotFoundException(f"User {ticket.assigned_to} not found")

        if ticket.team_id is not None:
            if not db.query(Team).filter(Team.id == ticket.team_id).first():
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
        new_ticket = _load_ticket(db, new_ticket.id)
        delete_by_prefix("tickets:all:")
        return _build_response(new_ticket)

    # ------------------------------------------------------------------ #
    # READ                                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_my_tickets(db: Session, current_user: User, limit: int, offset: int):
        """All tickets the agent created, is assigned to, or that belong to their team."""
        AgentTicketService._require_agent(current_user)
        cache_key = f"tickets:agent:{current_user.id}:{limit}:{offset}"
        cached = redis_client.get(cache_key)
        if cached:
            return [TicketResponse.model_validate(t) for t in json.loads(cached)]

        filters = [Ticket.created_by == current_user.id, Ticket.assigned_to == current_user.id]
        if current_user.team_id is not None:
            filters.append(Ticket.team_id == current_user.team_id)

        tickets = _load_tickets(
            db.query(Ticket).filter(or_(*filters))
        ).limit(limit).offset(offset).all()

        responses = [_build_response(t) for t in tickets]
        redis_client.setex(cache_key, 60 * 60, json.dumps([r.model_dump(mode="json") for r in responses]))
        return responses

    @staticmethod
    def get_ticket(id: int, db: Session, current_user: User):
        AgentTicketService._require_agent(current_user)
        cache_key = f"ticket:{id}"
        cached = redis_client.get(cache_key)
        if cached:
            data = json.loads(cached)
            if (
                data.get("created_by") != current_user.id
                and data.get("assigned_to") != current_user.id
                and data.get("team_id") != current_user.team_id
            ):
                raise PermissionDeniedException("You do not have access to this ticket")
            return TicketResponse.model_validate(data)

        ticket = _load_ticket(db, id)
        if not ticket:
            raise NotFoundException(f"Ticket {id} not found")
        if not AgentTicketService._is_accessible(ticket, current_user):
            raise PermissionDeniedException("You do not have access to this ticket")

        response = _build_response(ticket)
        redis_client.setex(cache_key, 60 * 60, json.dumps(response.model_dump(mode="json")))
        return response

    @staticmethod
    def get_created_tickets(db: Session, current_user: User, limit: int, offset: int):
        AgentTicketService._require_agent(current_user)
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
    def get_assigned_tickets(db: Session, current_user: User, limit: int, offset: int):
        AgentTicketService._require_agent(current_user)
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
    def get_team_tickets(db: Session, current_user: User, limit: int, offset: int):
        """Own team tickets only."""
        AgentTicketService._require_agent(current_user)
        if current_user.team_id is None:
            raise PermissionDeniedException("You are not assigned to a team")
        cache_key = f"tickets:team:{current_user.team_id}:{limit}:{offset}"
        cached = redis_client.get(cache_key)
        if cached:
            return [TicketResponse.model_validate(t) for t in json.loads(cached)]
        tickets = _load_tickets(
            db.query(Ticket).filter(Ticket.team_id == current_user.team_id)
        ).limit(limit).offset(offset).all()
        responses = [_build_response(t) for t in tickets]
        redis_client.setex(cache_key, 60 * 60, json.dumps([r.model_dump(mode="json") for r in responses]))
        return responses

    # ------------------------------------------------------------------ #
    # UPDATE                                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def update_ticket(id: int, ticket_update: TicketUpdate, db: Session, current_user: User):
        AgentTicketService._require_agent(current_user)

        ticket = _load_ticket(db, id)
        if not ticket:
            raise NotFoundException(f"Ticket {id} not found")

        if not AgentTicketService._is_accessible(ticket, current_user):
            raise PermissionDeniedException("You do not have access to this ticket")

        is_team_ticket = AgentTicketService._is_team_ticket(ticket, current_user)

        # title / description — agents cannot edit
        if ticket_update.title is not None or ticket_update.description is not None:
            raise PermissionDeniedException("Agents cannot edit ticket title or description")

        # priority — team tickets only
        if ticket_update.priority is not None:
            if not is_team_ticket:
                raise PermissionDeniedException("You can only change priority on your team's tickets")
            ticket.priority = ticket_update.priority

        # status — state machine enforced, team tickets only
        if ticket_update.status is not None:
            if not is_team_ticket:
                raise PermissionDeniedException("You can only change status on your team's tickets")
            allowed = VALID_TRANSITIONS.get(ticket.status, set())
            if ticket_update.status not in allowed:
                raise ValidationException(
                    f"Invalid transition: '{ticket.status.value}' → '{ticket_update.status.value}'. "
                    f"Allowed: {[s.value for s in allowed] or 'none (terminal state)'}"
                )
            ticket.status = ticket_update.status

        # assigned_to — team members only
        if ticket_update.assigned_to is not None:
            if not is_team_ticket:
                raise PermissionDeniedException("You can only reassign your team's tickets")
            target = db.query(User).filter(User.id == ticket_update.assigned_to).first()
            if not target:
                raise NotFoundException(f"User {ticket_update.assigned_to} not found")
            if target.team_id != current_user.team_id:
                raise PermissionDeniedException("You can only assign tickets to members of your own team")
            ticket.assigned_to = ticket_update.assigned_to

        # team_id — transfer allowed but cannot unassign (team_id=0); clears assignee on transfer
        if ticket_update.team_id is not None:
            if ticket_update.team_id == 0:
                raise PermissionDeniedException("Agents cannot unassign a ticket from a team")
            team = db.query(Team).filter(Team.id == ticket_update.team_id).first()
            if not team:
                raise NotFoundException(f"Team {ticket_update.team_id} not found")
            ticket.team_id = ticket_update.team_id
            ticket.assigned_to = None  # clear assignee when transferring teams

        db.commit()
        ticket = _load_ticket(db, id)

        redis_client.delete(f"ticket:{id}")
        delete_by_prefix("tickets:")
        return _build_response(ticket)


ticket_service_agent = AgentTicketService()