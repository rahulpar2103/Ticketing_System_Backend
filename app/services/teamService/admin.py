from app.schemas.teamSchema import TeamUpdate
import json
from app.db.redis import delete_by_prefix, safe_get, safe_setex, safe_delete
from app.schemas.userSchema import UserResponse
from app.core.exceptions import (
    AlreadyExistsException,
    PermissionDeniedException,
    NotFoundException,
    ValidationException,
)
from app.models.teamModel import Team
from app.core.security import require_role
from app.models.userModel import User, UserRole
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from app.schemas.teamSchema import TeamCreate, TeamResponse

TEAM_SORTABLE_FIELDS = {
    "created_at": Team.created_at,
    "updated_at": Team.updated_at,
    "name": Team.name,
}

MEMBER_SORTABLE_FIELDS = {
    "created_at": User.created_at,
    "name": User.name,
    "username": User.username,
}


class TeamServiceAdmin:

    def create_team(self, team: TeamCreate, current_user: User, db: Session):
        require_role(current_user, UserRole.admin)
        existing_team = db.query(Team).filter(Team.name == team.name).first()
        if existing_team:
            raise AlreadyExistsException(f"Team '{team.name}' already exists")
        new_team = Team(name=team.name, description=team.description)
        db.add(new_team)
        db.commit()
        db.refresh(new_team)
        delete_by_prefix("teams:")
        return TeamResponse.model_validate(new_team)

    def get_all_teams(
        self, current_user: User, db: Session, limit: int, offset: int,
        sort_by: str = "created_at", order: str = "desc",
    ):
        require_role(current_user, UserRole.admin)

        query = db.query(Team).filter(Team.is_active == True)

        # Sorting
        column = TEAM_SORTABLE_FIELDS.get(sort_by)
        if column is None:
            raise ValidationException(
                f"Invalid sort_by '{sort_by}'. Allowed: {list(TEAM_SORTABLE_FIELDS.keys())}"
            )
        if order not in ("asc", "desc"):
            raise ValidationException("Invalid order. Allowed: 'asc', 'desc'")
        order_func = asc if order == "asc" else desc
        query = query.order_by(order_func(column))

        total = query.count()
        teams = query.limit(limit).offset(offset).all()
        items = [TeamResponse.model_validate(t) for t in teams]
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total,
        }

    def get_team(self, id: int, current_user: User, db: Session):
        require_role(current_user, UserRole.admin)
        cache_key = f"team:{id}"
        cached = safe_get(cache_key)
        if cached:
            return TeamResponse.model_validate(json.loads(cached))
        team = db.query(Team).filter(Team.id == id, Team.is_active == True).first()
        if not team:
            raise NotFoundException(f"Team {id} not found")
        safe_setex(cache_key, 60 * 60 * 24, json.dumps(TeamResponse.model_validate(team).model_dump(mode="json")))
        return TeamResponse.model_validate(team)

    def get_team_members(
        self, team_id: int, current_user: User, db: Session, limit: int, offset: int,
        sort_by: str = "created_at", order: str = "desc",
    ):
        require_role(current_user, UserRole.admin)
        team = db.query(Team).filter(Team.id == team_id, Team.is_active == True).first()
        if not team:
            raise NotFoundException(f"Team {team_id} not found")

        query = db.query(User).filter(User.team_id == team_id, User.is_active == True)

        # Sorting
        column = MEMBER_SORTABLE_FIELDS.get(sort_by)
        if column is None:
            raise ValidationException(
                f"Invalid sort_by '{sort_by}'. Allowed: {list(MEMBER_SORTABLE_FIELDS.keys())}"
            )
        if order not in ("asc", "desc"):
            raise ValidationException("Invalid order. Allowed: 'asc', 'desc'")
        order_func = asc if order == "asc" else desc
        query = query.order_by(order_func(column))

        total = query.count()
        members = query.limit(limit).offset(offset).all()
        items = [UserResponse.model_validate(u) for u in members]
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total,
        }

    def update_team(self, id: int, team_update: TeamUpdate, current_user: User, db: Session):
        require_role(current_user, UserRole.admin)
        team = db.query(Team).filter(Team.id == id).first()
        if not team:
            raise NotFoundException(f"Team {id} not found")
        if team_update.name and team.name != team_update.name:
            existing = db.query(Team).filter(Team.name == team_update.name).first()
            if existing:
                raise AlreadyExistsException(f"Team '{team_update.name}' already exists")
        if team_update.name:
            team.name = team_update.name
        if team_update.description:
            team.description = team_update.description
        db.commit()
        db.refresh(team)
        safe_delete(f"team:{id}")

        delete_by_prefix("teams:")
        delete_by_prefix("tickets:")
        delete_by_prefix(f"team_members:{id}:")
        return {"message": f"Team {id} updated successfully"}

    def delete_team(self, id: int, current_user: User, db: Session):
        require_role(current_user, UserRole.admin)
        team = db.query(Team).filter(Team.id == id).first()
        if not team:
            raise NotFoundException(f"Team {id} not found")
        if not team.is_active:
            raise ValidationException(f"Team {id} is already deactivated")

        team.is_active = False

        # Cascade: clear team_id on all users in this team
        affected_users = db.query(User).filter(User.team_id == id).all()
        for user in affected_users:
            user.team_id = None

        # Cascade: unassign tickets from this team
        from app.models.ticketModel import Ticket
        affected_tickets = db.query(Ticket).filter(
            Ticket.team_id == id, Ticket.is_active == True
        ).all()
        for ticket in affected_tickets:
            ticket.team_id = None
            ticket.assigned_to = None

        db.commit()
        safe_delete(f"team:{id}")
        delete_by_prefix("teams:")
        delete_by_prefix(f"team_members:{id}:")
        delete_by_prefix("tickets:")
        delete_by_prefix("all_users:")
        return {
            "message": f"Team {id} deleted successfully",
            "cascaded": {
                "users_unassigned": len(affected_users),
                "tickets_unassigned": len(affected_tickets),
            }
        }

    def reactivate_team(self, id: int, current_user: User, db: Session):
        """Re-enable a soft-deleted team. Admin only."""
        require_role(current_user, UserRole.admin)
        team = db.query(Team).filter(Team.id == id, Team.is_active == False).first()
        if not team:
            raise NotFoundException(f"Team {id} not found or is already active")
        team.is_active = True
        db.commit()
        safe_delete(f"team:{id}")
        delete_by_prefix("teams:")
        return {"message": f"Team {id} reactivated successfully"}

    def get_team_stats(self, team_id: int, current_user: User, db: Session):
        """Get per-team ticket statistics. Admin only."""
        require_role(current_user, UserRole.admin)
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise NotFoundException(f"Team {team_id} not found")

        from app.models.ticketModel import Ticket, TicketStatus
        from sqlalchemy import func

        base_filter = [Ticket.team_id == team_id, Ticket.is_active == True]

        total_tickets = db.query(Ticket).filter(*base_filter).count()
        member_count = db.query(User).filter(
            User.team_id == team_id, User.is_active == True
        ).count()

        # By status
        status_counts = {}
        status_rows = (
            db.query(Ticket.status, func.count(Ticket.id))
            .filter(*base_filter)
            .group_by(Ticket.status)
            .all()
        )
        for s in TicketStatus:
            status_counts[s.value] = 0
        for status, count in status_rows:
            status_counts[status.value] = count

        # Unassigned
        unassigned = db.query(Ticket).filter(
            *base_filter, Ticket.assigned_to == None
        ).count()

        return {
            "team_id": team_id,
            "team_name": team.name,
            "is_active": team.is_active,
            "member_count": member_count,
            "total_tickets": total_tickets,
            "by_status": status_counts,
            "unassigned_tickets": unassigned,
        }


team_service_admin = TeamServiceAdmin()