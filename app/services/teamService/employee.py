import json
from app.db.redis import safe_get, safe_setex, safe_delete
from app.schemas.userSchema import UserResponse
from app.core.exceptions import PermissionDeniedException, NotFoundException
from app.models.teamModel import Team
from app.models.userModel import User
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from app.schemas.teamSchema import TeamResponse


class TeamServiceEmployee:

    def get_team(self, id: int, current_user: User, db: Session):
        if current_user.role.value != "employee":
            raise PermissionDeniedException("You are not authorized to hit this endpoint")
        if current_user.team_id is None:
            raise PermissionDeniedException("You are not assigned to a team")
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

    def get_team_members(self, team_id: int, current_user: User, db: Session, limit: int, offset: int):
        if current_user.role.value != "employee":
            raise PermissionDeniedException("You are not authorized to hit this endpoint")
        if current_user.team_id is None:
            raise PermissionDeniedException("You are not assigned to a team")
        if current_user.team_id != team_id:
            raise PermissionDeniedException("You are not authorized to get members of this team")
        team = db.query(Team).filter(Team.id == team_id, Team.is_active == True).first()
        if not team:
            raise NotFoundException(f"Team {team_id} not found")
        cache_key = f"team_members:{team_id}:{limit}:{offset}"
        cached = safe_get(cache_key)
        if cached:
            return [UserResponse.model_validate(u) for u in json.loads(cached)]
        members = db.query(User).filter(User.team_id == team_id, User.is_active == True).limit(limit).offset(offset).all()
        serialized = [UserResponse.model_validate(u).model_dump(mode="json") for u in members]
        safe_setex(cache_key, 60 * 60 * 24, json.dumps(serialized))
        return [UserResponse.model_validate(u) for u in members]


team_service_employee = TeamServiceEmployee()