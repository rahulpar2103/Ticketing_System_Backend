from app.schemas.teamSchema import TeamUpdate
import json
from app.db.redis import delete_by_prefix, safe_get, safe_setex, safe_delete
from app.schemas.userSchema import UserResponse
from app.core.exceptions import (
    AlreadyExistsException,
    PermissionDeniedException,
    NotFoundException,
)
from app.models.teamModel import Team
from app.models.userModel import User
from sqlalchemy.orm import Session
from app.schemas.teamSchema import TeamCreate, TeamResponse


class TeamServiceAdmin:

    def create_team(self, team: TeamCreate, current_user: User, db: Session):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("You are not authorized to create a team")
        existing_team = db.query(Team).filter(Team.name == team.name).first()
        if existing_team:
            raise AlreadyExistsException(f"Team '{team.name}' already exists")
        new_team = Team(name=team.name, description=team.description)
        db.add(new_team)
        db.commit()
        db.refresh(new_team)
        delete_by_prefix("teams:")
        return TeamResponse.model_validate(new_team)

    def get_all_teams(self, current_user: User, db: Session, limit: int, offset: int):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("You are not authorized to get all teams")
        cache_key = f"teams:{limit}:{offset}"
        cached = safe_get(cache_key)
        if cached:
            return [TeamResponse.model_validate(t) for t in json.loads(cached)]
        teams = db.query(Team).filter(Team.is_active == True).limit(limit).offset(offset).all()
        serialized = [TeamResponse.model_validate(t).model_dump(mode="json") for t in teams]
        safe_setex(cache_key, 60 * 60 * 24, json.dumps(serialized))
        return [TeamResponse.model_validate(t) for t in teams]

    def get_team(self, id: int, current_user: User, db: Session):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("You are not authorized to get a team")
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
        if current_user.role.value != "admin":
            raise PermissionDeniedException("You are not authorized to get team members")
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

    def update_team(self, id: int, team_update: TeamUpdate, current_user: User, db: Session):
        if current_user.role.value != "admin":
            raise PermissionDeniedException("You are not authorized to update a team")
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
        if current_user.role.value != "admin":
            raise PermissionDeniedException("You are not authorized to delete a team")
        team = db.query(Team).filter(Team.id == id).first()
        if not team:
            raise NotFoundException(f"Team {id} not found")
        team.is_active = False
        db.commit()
        safe_delete(f"team:{id}")
        delete_by_prefix("teams:")
        delete_by_prefix(f"team_members:{id}:")
        delete_by_prefix("tickets:")
        delete_by_prefix("all_users:")
        return {"message": f"Team {id} deleted successfully"}


team_service_admin = TeamServiceAdmin()