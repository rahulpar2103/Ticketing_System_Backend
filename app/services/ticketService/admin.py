from app.services.auditService import log_audit_event
from app.db.redis import safe_delete
from app.db.redis import safe_setex
from app.db.redis import safe_get
from app.models.ticketModel import TicketStatus
import json
from sqlalchemy.orm import Session
from app.db.redis import delete_by_prefix
from app.models.ticketModel import Ticket
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

class AdminTicketService:

    def create_ticket(self, ticket: TicketCreate, db: Session, current_user: User):
        require_role(current_user, UserRole.admin)

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
            if not assigned_user.is_active:
                raise ValidationException(f"User {assigned_user.username} is deactivated and cannot be assigned")

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
        db.flush()
        log_audit_event(db, new_ticket.id, current_user, "CREATED")
        db.commit()
        new_ticket = _load_ticket(db, new_ticket.id)
        if not new_ticket:
            raise NotFoundException(f"Ticket {new_ticket.id} not found")
        delete_by_prefix("tickets:")
        return _build_response(new_ticket)
    
    def get_all_tickets(
        self, db: Session, current_user: User, limit: int, offset: int,
        search: str | None = None, status: str | None = None,
        priority: str | None = None, sort_by: str = "created_at", order: str = "desc",
    ):
        require_role(current_user, UserRole.admin)

        query = db.query(Ticket).filter(Ticket.is_active == True)
        query = apply_ticket_filters(query, search, status, priority)
        query = apply_ticket_sorting(query, sort_by, order)
        return paginate_tickets(query, limit, offset)

    def get_ticket(self, id: int, db: Session, current_user: User):
        require_role(current_user, UserRole.admin)
        cache_key = f"ticket:{id}"
        cached = safe_get(cache_key)
        if cached:
            return TicketResponse.model_validate(json.loads(cached))
        ticket = _load_ticket(db, id)
        if not ticket:
            raise NotFoundException(f"Ticket {id} not found")
        response = _build_response(ticket)
        safe_setex(cache_key, 60 * 60, json.dumps(response.model_dump(mode="json")))
        return response

    def get_assigned_tickets(
        self, db: Session, current_user: User, limit: int, offset: int,
        search: str | None = None, status: str | None = None,
        priority: str | None = None, sort_by: str = "created_at", order: str = "desc",
    ):
        require_role(current_user, UserRole.admin)

        query = db.query(Ticket).filter(
            Ticket.assigned_to == current_user.id, Ticket.is_active == True
        )
        query = apply_ticket_filters(query, search, status, priority)
        query = apply_ticket_sorting(query, sort_by, order)
        return paginate_tickets(query, limit, offset)

    def get_created_tickets(
        self, db: Session, current_user: User, limit: int, offset: int,
        search: str | None = None, status: str | None = None,
        priority: str | None = None, sort_by: str = "created_at", order: str = "desc",
    ):
        require_role(current_user, UserRole.admin)

        query = db.query(Ticket).filter(
            Ticket.created_by == current_user.id, Ticket.is_active == True
        )
        query = apply_ticket_filters(query, search, status, priority)
        query = apply_ticket_sorting(query, sort_by, order)
        return paginate_tickets(query, limit, offset)

    def get_team_tickets(
        self, team_id: int, db: Session, current_user: User, limit: int, offset: int,
        search: str | None = None, status: str | None = None,
        priority: str | None = None, sort_by: str = "created_at", order: str = "desc",
    ):
        require_role(current_user, UserRole.admin)
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise NotFoundException(f"Team {team_id} not found")

        query = db.query(Ticket).filter(
            Ticket.team_id == team_id, Ticket.is_active == True
        )
        query = apply_ticket_filters(query, search, status, priority)
        query = apply_ticket_sorting(query, sort_by, order)
        return paginate_tickets(query, limit, offset)

    def get_tickets_assigned_to_user(
        self, user_id: int, db: Session, current_user: User, limit: int, offset: int,
        search: str | None = None, status: str | None = None,
        priority: str | None = None, sort_by: str = "created_at", order: str = "desc",
    ):
        require_role(current_user, UserRole.admin)

        query = db.query(Ticket).filter(
            Ticket.assigned_to == user_id, Ticket.is_active == True
        )
        query = apply_ticket_filters(query, search, status, priority)
        query = apply_ticket_sorting(query, sort_by, order)
        return paginate_tickets(query, limit, offset)

    def update_ticket(self, id: int, ticket_update: TicketUpdate, db: Session, current_user: User):
        require_role(current_user, UserRole.admin)

        ticket = db.query(Ticket).filter(Ticket.id == id, Ticket.is_active == True).first()
        if not ticket:
            raise NotFoundException(f"Ticket {id} not found")

        if ticket_update.title is not None:
            ticket.title = ticket_update.title
        if ticket_update.description is not None:
            ticket.description = ticket_update.description
        if ticket_update.status is not None:
            ticket.status = ticket_update.status
            if ticket_update.status == TicketStatus.resolved:
                ticket.resolved_at = datetime.now(timezone.utc)
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
            if not new_assignee.is_active:
                raise ValidationException(f"User {new_assignee.username} is deactivated and cannot be assigned")

        new_team = None
        if ticket_update.team_id is not None:
            new_team = db.query(Team).filter(Team.id == ticket_update.team_id).first()
            if not new_team:
                raise NotFoundException(f"Team {ticket_update.team_id} not found")
            if not new_team.is_active:
                raise ValidationException(f"Team {ticket_update.team_id} is deactivated and cannot be assigned")

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

        log_audit_event(db, id, current_user, "UPDATED", ticket_update.model_dump(exclude_unset=True, mode='json'))

        db.commit()

        ticket = _load_ticket(db, id)
        if not ticket:
            raise NotFoundException(f"Ticket {id} not found")
        safe_delete(f"ticket:{id}")
        delete_by_prefix("tickets:")
        return _build_response(ticket)

    def delete_ticket(self, id: int, db: Session, current_user: User):
        """Soft-delete a ticket. Admin only."""
        require_role(current_user, UserRole.admin)
        ticket = db.query(Ticket).filter(Ticket.id == id, Ticket.is_active == True).first()
        if not ticket:
            raise NotFoundException(f"Ticket {id} not found")
        ticket.is_active = False
        log_audit_event(db, id, current_user, "DELETED")
        db.commit()
        safe_delete(f"ticket:{id}")
        delete_by_prefix("tickets:")
        delete_by_prefix(f"comments:ticket:{id}:")
        return {"message": f"Ticket {id} deleted successfully"}

    def get_ticket_stats(self, db: Session, current_user: User, team_id: int | None = None):
        """Get ticket statistics (counts by status and priority) scoped by user role."""
        from app.models.ticketModel import Priority
        from sqlalchemy import func, or_

        if current_user.role == UserRole.admin:
            query = db.query(Ticket).filter(Ticket.is_active == True)
            if team_id is not None:
                team = db.query(Team).filter(Team.id == team_id).first()
                if not team:
                    raise NotFoundException(f"Team {team_id} not found")
                query = query.filter(Ticket.team_id == team_id)

            total = query.count()

            # By status
            status_counts = {s.value: 0 for s in TicketStatus}
            status_rows = (
                db.query(Ticket.status, func.count(Ticket.id))
                .filter(Ticket.is_active == True, *([Ticket.team_id == team_id] if team_id else []))
                .group_by(Ticket.status)
                .all()
            )
            for status, count in status_rows:
                status_counts[status.value] = count

            # By priority
            priority_counts = {p.value: 0 for p in Priority}
            priority_rows = (
                db.query(Ticket.priority, func.count(Ticket.id))
                .filter(Ticket.is_active == True, *([Ticket.team_id == team_id] if team_id else []))
                .group_by(Ticket.priority)
                .all()
            )
            for priority, count in priority_rows:
                priority_counts[priority.value] = count

            # Unassigned count
            unassigned_filter = [Ticket.is_active == True, Ticket.assigned_to == None]
            if team_id:
                unassigned_filter.append(Ticket.team_id == team_id)
            unassigned = db.query(Ticket).filter(*unassigned_filter).count()

            return {
                "total": total,
                "by_status": status_counts,
                "by_priority": priority_counts,
                "unassigned": unassigned,
            }

        elif current_user.role == UserRole.agent:
            filters = [Ticket.created_by == current_user.id, Ticket.assigned_to == current_user.id]
            if current_user.team_id is not None:
                filters.append(Ticket.team_id == current_user.team_id)
            base_filter = or_(*filters)

            query = db.query(Ticket).filter(base_filter, Ticket.is_active == True)
            total = query.count()

            # By status
            status_counts = {s.value: 0 for s in TicketStatus}
            status_rows = (
                db.query(Ticket.status, func.count(Ticket.id))
                .filter(base_filter, Ticket.is_active == True)
                .group_by(Ticket.status)
                .all()
            )
            for status, count in status_rows:
                status_counts[status.value] = count

            # By priority
            priority_counts = {p.value: 0 for p in Priority}
            priority_rows = (
                db.query(Ticket.priority, func.count(Ticket.id))
                .filter(base_filter, Ticket.is_active == True)
                .group_by(Ticket.priority)
                .all()
            )
            for priority, count in priority_rows:
                priority_counts[priority.value] = count

            # Assigned to me count
            assigned_to_me = db.query(Ticket).filter(
                Ticket.assigned_to == current_user.id,
                Ticket.is_active == True
            ).count()

            return {
                "total": total,
                "by_status": status_counts,
                "by_priority": priority_counts,
                "assignedToMe": assigned_to_me,
                "assigned_to_me": assigned_to_me,
            }

        else: # Employee
            base_filter = or_(Ticket.created_by == current_user.id, Ticket.assigned_to == current_user.id)

            query = db.query(Ticket).filter(base_filter, Ticket.is_active == True)
            total = query.count()

            # By status
            status_counts = {s.value: 0 for s in TicketStatus}
            status_rows = (
                db.query(Ticket.status, func.count(Ticket.id))
                .filter(base_filter, Ticket.is_active == True)
                .group_by(Ticket.status)
                .all()
            )
            for status, count in status_rows:
                status_counts[status.value] = count

            active_count = status_counts.get("open", 0) + status_counts.get("in_progress", 0)
            resolved_count = status_counts.get("resolved", 0) + status_counts.get("closed", 0)

            return {
                "total": total,
                "by_status": status_counts,
                "active": active_count,
                "resolved": resolved_count,
            }

    def reactivate_ticket(self, id: int, db: Session, current_user: User):
        """Re-enable a soft-deleted ticket. Admin only."""
        require_role(current_user, UserRole.admin)
        ticket = db.query(Ticket).filter(Ticket.id == id, Ticket.is_active == False).first()
        if not ticket:
            raise NotFoundException(f"Ticket {id} not found or is already active")
        ticket.is_active = True
        db.commit()
        safe_delete(f"ticket:{id}")
        delete_by_prefix("tickets:")
        return {"message": f"Ticket {id} reactivated successfully"}

ticket_service_admin = AdminTicketService()