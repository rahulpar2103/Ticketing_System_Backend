import json
from app.db.redis import safe_get, safe_setex
from app.schemas.userSchema import UserResponse
from app.core.exceptions import PermissionDeniedException, NotFoundException, ValidationException
from app.models.teamModel import Team
from app.core.security import require_role
from app.models.userModel import User, UserRole
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from app.schemas.teamSchema import TeamResponse

MEMBER_SORTABLE_FIELDS = {
    "created_at": User.created_at,
    "name": User.name,
    "username": User.username,
}


class TeamServiceAgent:

    def get_team(self, id: int, current_user: User, db: Session):
        require_role(current_user, UserRole.agent)
        if current_user.team_id != id:
            raise PermissionDeniedException("You can only view your own team")
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
        require_role(current_user, UserRole.agent)
        if current_user.team_id != team_id:
            raise PermissionDeniedException("You are not authorized to get members of this team")
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


team_service_agent = TeamServiceAgent()