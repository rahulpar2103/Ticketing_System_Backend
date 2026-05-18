import json
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.db.redis import delete_by_prefix, safe_delete, safe_setex, safe_get    
from app.models.ticketModel import Ticket, TicketStatus
from app.models.userModel import User, UserRole
from app.schemas.ticketSchema import TicketCreate, TicketUpdate, TicketResponse
from app.core.exceptions import NotFoundException, PermissionDeniedException, ValidationException
from app.services.ticketService.utils import _build_response, _load_ticket, _load_tickets


class EmployeeTicketService:

    def _require_employee(self, current_user: User):
        if current_user.role != UserRole.employee:
            raise PermissionDeniedException("Not allowed to access this endpoint")

    def _is_accessible(self, ticket: Ticket, current_user: User) -> bool:
        """Employee can only see tickets they created or that are assigned to them."""
        return (
            ticket.created_by == current_user.id
            or ticket.assigned_to == current_user.id
        )

    # ------------------------------------------------------------------ #
    # CREATE                                                               #
    # ------------------------------------------------------------------ #

    def create_ticket(self, ticket: TicketCreate, db: Session, current_user: User):
        self._require_employee(current_user)

        # Employees cannot set assignee or team
        if ticket.assigned_to is not None:
            raise PermissionDeniedException("Employees cannot set an assignee on ticket creation")
        if ticket.team_id is not None:
            raise PermissionDeniedException("Employees cannot assign a ticket to a team on creation")

        new_ticket = Ticket(
            title=ticket.title,
            description=ticket.description,
            priority=ticket.priority,
            created_by=current_user.id,
        )
        db.add(new_ticket)
        db.commit()
        new_ticket = _load_ticket(db, new_ticket.id)
        delete_by_prefix("tickets:")
        return _build_response(new_ticket)

    # ------------------------------------------------------------------ #
    # READ                                                                 #
    # ------------------------------------------------------------------ #

    def get_my_tickets(self, db: Session, current_user: User, limit: int, offset: int):
        """Tickets the employee created or is assigned to."""
        self._require_employee(current_user)
        cache_key = f"tickets:employee:{current_user.id}:{limit}:{offset}"
        cached = safe_get(cache_key)
        if cached:
            return [TicketResponse.model_validate(t) for t in json.loads(cached)]

        tickets = _load_tickets(
            db.query(Ticket).filter(
            or_(Ticket.created_by == current_user.id, Ticket.assigned_to == current_user.id),
            Ticket.is_active == True
        )
        ).limit(limit).offset(offset).all()

        responses = [_build_response(t) for t in tickets]
        safe_setex(cache_key, 60 * 60, json.dumps([r.model_dump(mode="json") for r in responses]))
        return responses

    def get_ticket(self, id: int, db: Session, current_user: User):
        self._require_employee(current_user)
        cache_key = f"ticket:{id}"
        cached = safe_get(cache_key)
        if cached:
            data = json.loads(cached)
            if (
                data.get("created_by") != current_user.id
                and data.get("assigned_to") != current_user.id
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

    def get_created_tickets(self, db: Session, current_user: User, limit: int, offset: int):
        self._require_employee(current_user)
        cache_key = f"tickets:created:{current_user.id}:{limit}:{offset}"
        cached = safe_get(cache_key)
        if cached:
            return [TicketResponse.model_validate(t) for t in json.loads(cached)]
        tickets = _load_tickets(
            db.query(Ticket).filter(Ticket.created_by == current_user.id, Ticket.is_active == True)
        ).limit(limit).offset(offset).all()
        responses = [_build_response(t) for t in tickets]
        safe_setex(cache_key, 60 * 60, json.dumps([r.model_dump(mode="json") for r in responses]))
        return responses

    def get_assigned_tickets(self, db: Session, current_user: User, limit: int, offset: int):
        self._require_employee(current_user)
        cache_key = f"tickets:assigned:{current_user.id}:{limit}:{offset}"
        cached = safe_get(cache_key)
        if cached:
            return [TicketResponse.model_validate(t) for t in json.loads(cached)]
        tickets = _load_tickets(
            db.query(Ticket).filter(Ticket.assigned_to == current_user.id, Ticket.is_active == True)
        ).limit(limit).offset(offset).all()
        responses = [_build_response(t) for t in tickets]
        safe_setex(cache_key, 60 * 60, json.dumps([r.model_dump(mode="json") for r in responses]))
        return responses

    # ------------------------------------------------------------------ #
    # UPDATE                                                               #
    # ------------------------------------------------------------------ #

    def update_ticket(self, id: int, ticket_update: TicketUpdate, db: Session, current_user: User):
        self._require_employee(current_user)

        ticket = _load_ticket(db, id)
        if not ticket:
            raise NotFoundException(f"Ticket {id} not found")

        # Employees can only edit their own created tickets
        if ticket.created_by != current_user.id:
            raise PermissionDeniedException("You can only edit tickets you created")

        # title / description — own ticket, open status only
        if ticket_update.title is not None or ticket_update.description is not None:
            if ticket.status != TicketStatus.open:
                raise PermissionDeniedException("You can only edit title or description on open tickets")
            if ticket_update.title is not None:
                ticket.title = ticket_update.title
            if ticket_update.description is not None:
                ticket.description = ticket_update.description

        # priority — not allowed
        if ticket_update.priority is not None:
            raise PermissionDeniedException("Employees cannot change ticket priority")

        # status — open → closed (cancel) or resolved → closed (confirm fix)
        if ticket_update.status is not None:
            allowed_transitions = {
                TicketStatus.open: TicketStatus.closed,
                TicketStatus.resolved: TicketStatus.closed,
            }
            expected = allowed_transitions.get(ticket.status)
            if expected is None or ticket_update.status != expected:
                raise ValidationException(
                    "Employees can only close their own tickets (open → closed or resolved → closed)"
                )
            ticket.status = ticket_update.status

        # assigned_to — not allowed
        if ticket_update.assigned_to is not None:
            raise PermissionDeniedException("Employees cannot reassign tickets")

        # team_id — not allowed
        if ticket_update.team_id is not None:
            raise PermissionDeniedException("Employees cannot transfer tickets to a team")

        db.commit()
        ticket = _load_ticket(db, id)

        safe_delete(f"ticket:{id}")
        delete_by_prefix("tickets:")
        return _build_response(ticket)


ticket_service_employee = EmployeeTicketService()