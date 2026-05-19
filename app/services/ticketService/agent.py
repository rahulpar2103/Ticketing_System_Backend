from app.db.redis import safe_delete
from app.db.redis import safe_setex
from app.db.redis import safe_get
import json
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.db.redis import delete_by_prefix
from app.models.ticketModel import Ticket, TicketStatus
from app.models.teamModel import Team
from app.core.security import require_role
from app.models.userModel import User, UserRole
from app.schemas.ticketSchema import TicketCreate, TicketUpdate, TicketResponse
from app.core.exceptions import NotFoundException, PermissionDeniedException, ValidationException
from app.services.ticketService.utils import (
    _build_response, _load_ticket, _load_tickets,
    apply_ticket_filters, apply_ticket_sorting, paginate_tickets,
)
from datetime import datetime, timezone

VALID_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.open:        {TicketStatus.in_progress},
    TicketStatus.in_progress: {TicketStatus.resolved},
    TicketStatus.resolved:    {TicketStatus.closed},
    TicketStatus.closed:      set(),
}


class AgentTicketService:

    def _require_agent(self, current_user: User):
        require_role(current_user, UserRole.agent)

    def _is_accessible(self, ticket: Ticket, current_user: User) -> bool:
        """Ticket is accessible if the agent created it, is assigned to it, or it belongs to their team."""
        return (
            ticket.created_by == current_user.id
            or ticket.assigned_to == current_user.id
            or (current_user.team_id is not None and ticket.team_id == current_user.team_id)
        )

    def _is_team_ticket(self, ticket: Ticket, current_user: User) -> bool:
        return current_user.team_id is not None and ticket.team_id == current_user.team_id

    def create_ticket(self, ticket: TicketCreate, db: Session, current_user: User):
        self._require_agent(current_user)

        if ticket.assigned_to == -1:
            ticket.assigned_to = None
        if ticket.team_id == 0:
            ticket.team_id = None

        assigned_user = None
        if ticket.assigned_to is not None:
            assigned_user = db.query(User).filter(User.id == ticket.assigned_to).first()
            if not assigned_user:
                raise NotFoundException(f"User {ticket.assigned_to} not found")
            if not assigned_user.is_active:
                raise ValidationException(f"User {assigned_user.username} is deactivated and cannot be assigned")
            if assigned_user.team_id != current_user.team_id:
                raise PermissionDeniedException("You can only assign tickets to members of your own team")

        if ticket.team_id is not None:
            team = db.query(Team).filter(Team.id == ticket.team_id).first()
            if not team:
                raise NotFoundException(f"Team {ticket.team_id} not found")
            if not team.is_active:
                raise ValidationException(f"Team {ticket.team_id} is deactivated and cannot be assigned")
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
        
        ticket_id = new_ticket.id
        new_ticket = _load_ticket(db, ticket_id)
        if not new_ticket:
            raise NotFoundException(f"Ticket {ticket_id} not found")
        delete_by_prefix("tickets:")
        return _build_response(new_ticket)

    def get_my_tickets(
        self, db: Session, current_user: User, limit: int, offset: int,
        search: str | None = None, status: str | None = None,
        priority: str | None = None, sort_by: str = "created_at", order: str = "desc",
    ):
        """All tickets the agent created, is assigned to, or that belong to their team."""
        self._require_agent(current_user)

        filters = [Ticket.created_by == current_user.id, Ticket.assigned_to == current_user.id]
        if current_user.team_id is not None:
            filters.append(Ticket.team_id == current_user.team_id)

        query = db.query(Ticket).filter(or_(*filters), Ticket.is_active == True)
        query = apply_ticket_filters(query, search, status, priority)
        query = apply_ticket_sorting(query, sort_by, order)
        return paginate_tickets(query, limit, offset)

    def get_ticket(self, id: int, db: Session, current_user: User):
        self._require_agent(current_user)
        cache_key = f"ticket:{id}"
        cached = safe_get(cache_key)
        if cached:
            data = json.loads(cached)
            team_id_match = (
                current_user.team_id is not None
                and data.get("team_id") == current_user.team_id
            )
            if (
                data.get("created_by") != current_user.id
                and data.get("assigned_to") != current_user.id
                and not team_id_match
            ):
                raise PermissionDeniedException("You do not have access to this ticket")
            return TicketResponse.model_validate(data)

        ticket = _load_ticket(db, id)
        if not ticket:
            raise NotFoundException(f"Ticket {id} not found")
        if not self._is_accessible(ticket, current_user):
            raise PermissionDeniedException("You do not have access to this ticket")

        response = _build_response(ticket)
        safe_setex(cache_key, 60 * 60, json.dumps(response.model_dump(mode="json")))
        return response

    def get_created_tickets(
        self, db: Session, current_user: User, limit: int, offset: int,
        search: str | None = None, status: str | None = None,
        priority: str | None = None, sort_by: str = "created_at", order: str = "desc",
    ):
        self._require_agent(current_user)

        query = db.query(Ticket).filter(
            Ticket.created_by == current_user.id, Ticket.is_active == True
        )
        query = apply_ticket_filters(query, search, status, priority)
        query = apply_ticket_sorting(query, sort_by, order)
        return paginate_tickets(query, limit, offset)

    def get_assigned_tickets(
        self, db: Session, current_user: User, limit: int, offset: int,
        search: str | None = None, status: str | None = None,
        priority: str | None = None, sort_by: str = "created_at", order: str = "desc",
    ):
        self._require_agent(current_user)

        query = db.query(Ticket).filter(
            Ticket.assigned_to == current_user.id, Ticket.is_active == True
        )
        query = apply_ticket_filters(query, search, status, priority)
        query = apply_ticket_sorting(query, sort_by, order)
        return paginate_tickets(query, limit, offset)

    def get_team_tickets(
        self, db: Session, current_user: User, limit: int, offset: int,
        search: str | None = None, status: str | None = None,
        priority: str | None = None, sort_by: str = "created_at", order: str = "desc",
    ):
        """Own team tickets only."""
        self._require_agent(current_user)
        if current_user.team_id is None:
            raise PermissionDeniedException("You are not assigned to a team")

        query = db.query(Ticket).filter(
            Ticket.team_id == current_user.team_id, Ticket.is_active == True
        )
        query = apply_ticket_filters(query, search, status, priority)
        query = apply_ticket_sorting(query, sort_by, order)
        return paginate_tickets(query, limit, offset)

    def update_ticket(self, id: int, ticket_update: TicketUpdate, db: Session, current_user: User):
        self._require_agent(current_user)

        ticket = _load_ticket(db, id)
        if not ticket:
            raise NotFoundException(f"Ticket {id} not found")

        if not self._is_accessible(ticket, current_user):
            raise PermissionDeniedException("You do not have access to this ticket")

        is_team_ticket = self._is_team_ticket(ticket, current_user)
        is_creator = ticket.created_by == current_user.id
        is_assignee = ticket.assigned_to == current_user.id

        if ticket_update.title is not None or ticket_update.description is not None:
            if not is_creator:
                raise PermissionDeniedException("You can only edit title or description on tickets you created")
            if ticket_update.title is not None:
                ticket.title = ticket_update.title
            if ticket_update.description is not None:
                ticket.description = ticket_update.description

        if ticket_update.priority is not None:
            if not is_team_ticket:
                raise PermissionDeniedException("You can only change priority on your team's tickets")
            ticket.priority = ticket_update.priority

        if ticket_update.status is not None:
            if not (is_creator or is_assignee or is_team_ticket):
                raise PermissionDeniedException("You do not have permission to change the status of this ticket")
            allowed = VALID_TRANSITIONS.get(ticket.status, set())
            if ticket_update.status not in allowed:
                raise ValidationException(
                    f"Invalid transition: '{ticket.status.value}' → '{ticket_update.status.value}'. "
                    f"Allowed: {[s.value for s in allowed] or 'none (terminal state)'}"
                )
            ticket.status = ticket_update.status
            if ticket_update.status == TicketStatus.resolved:
                ticket.resolved_at = datetime.now(timezone.utc)

        if ticket_update.assigned_to == -1:
            if not is_team_ticket:
                raise PermissionDeniedException("You can only reassign your team's tickets")
            ticket.assigned_to = None
        elif ticket_update.assigned_to is not None:
            if not is_team_ticket:
                raise PermissionDeniedException("You can only reassign your team's tickets")
            target = db.query(User).filter(User.id == ticket_update.assigned_to).first()
            if not target:
                raise NotFoundException(f"User {ticket_update.assigned_to} not found")
            if not target.is_active:
                raise ValidationException(f"User {target.username} is deactivated and cannot be assigned")
            if target.team_id != current_user.team_id:
                raise PermissionDeniedException("You can only assign tickets to members of your own team")
            ticket.assigned_to = ticket_update.assigned_to

        if ticket_update.team_id is not None:
            if ticket_update.team_id == 0:
                raise PermissionDeniedException("Agents cannot unassign a ticket from a team")
            team = db.query(Team).filter(Team.id == ticket_update.team_id).first()
            if not team:
                raise NotFoundException(f"Team {ticket_update.team_id} not found")
            if not team.is_active:
                raise ValidationException(f"Team {ticket_update.team_id} is deactivated and cannot be assigned")
            ticket.team_id = ticket_update.team_id
            ticket.assigned_to = None

        db.commit()
        ticket = _load_ticket(db, id)

        if not ticket:
            raise NotFoundException(f"Ticket {id} not found")
        safe_delete(f"ticket:{id}")
        delete_by_prefix("tickets:")
        return _build_response(ticket)

    def delete_ticket(self, id: int, db: Session, current_user: User):
        """Soft-delete a ticket. Agent can delete tickets in their team or that they created."""
        self._require_agent(current_user)
        ticket = db.query(Ticket).filter(Ticket.id == id, Ticket.is_active == True).first()
        if not ticket:
            raise NotFoundException(f"Ticket {id} not found")
        if not self._is_accessible(ticket, current_user):
            raise PermissionDeniedException("You do not have access to this ticket")
        ticket.is_active = False
        db.commit()
        safe_delete(f"ticket:{id}")
        delete_by_prefix("tickets:")
        delete_by_prefix(f"comments:ticket:{id}:")
        return {"message": f"Ticket {id} deleted successfully"}

ticket_service_agent = AgentTicketService()