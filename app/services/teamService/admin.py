# pyrefly: ignore [missing-import]
from app.db.redis import delete_by_prefix
from app.schemas.userSchema import UserResponse
from app.core.exceptions import AlreadyExistsException, PermissionDeniedException, NotFoundException, UnauthorizedException, InvalidCredentialsException, MissingCredentialException
from app.models.teamModel import Team
# pyrefly: ignore [missing-import]
from app.models.userModel import User
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from app.schemas.teamSchema import TeamCreate, TeamResponse
# pyrefly: ignore [missing-import]
from app.models.userModel import User
# pyrefly: ignore [missing-import]
from app.db.redis import redis_client

class TeamServiceAdmin:
    def create_team(self,team: TeamCreate,current_user:User, db: Session):
        if current_user.role != "admin":
            raise PermissionDeniedException("You are not authorized to create a team")
        existing_team=db.query(Team).filter(Team.name==team.name).first()
        if existing_team:
            raise AlreadyExistsException(f"Team {team.name} already exists")
        new_team=Team(
            name=team.name,
            description=team.description
        )
        db.add(new_team)
        db.commit()
        db.refresh(new_team)
        return TeamResponse.model_validate(new_team)

    def get_all_teams(self, current_user:User, db: Session, limit: int, offset: int):
        if current_user.role != "admin":
            raise PermissionDeniedException("You are not authorized to get all teams")
        cache_key=f"teams:{limit}:{offset}"
        cached_teams=redis_client.get(cache_key)
        if cached_teams:
            return cached_teams
        teams=db.query(Team).all()
        redis_client.setex(cache_key,60*60*24,[TeamResponse.model_validate(team) for team in teams])
        return [TeamResponse.model_validate(team) for team in teams]

    def get_team(self, id: int, current_user:User, db: Session):
        if current_user.role != "admin":
            raise PermissionDeniedException("You are not authorized to get a team")
        cache_key=f"team:{id}"
        cached_team=redis_client.get(cache_key)
        if cached_team:
            return cached_team
        team=db.query(Team).filter(Team.id==id).first()
        if not team:
            raise NotFoundException(f"Team {id} not found")
        redis_client.setex(cache_key,60*60*24,TeamResponse.model_validate(team))
        return TeamResponse.model_validate(team)

    def get_team_members(self, team_id: int, current_user:User, db: Session, limit: int, offset: int):
        if current_user.role != "admin":
            raise PermissionDeniedException("You are not authorized to get team members")
        cache_key=f"team_members:{team_id}:{limit}:{offset}"
        cached_team_members=redis_client.get(cache_key)
        if cached_team_members:
            return cached_team_members
        team_members=db.query(User).filter(User.team_id==team_id).all()
        if not team_members:
            raise NotFoundException(f"Team {team_id} not found")
        redis_client.setex(cache_key,60*60*24,[UserResponse.model_validate(user) for user in team_members])
        return [UserResponse.model_validate(user) for user in team_members]

    def update_team(self, id: int, team_update: TeamCreate, current_user:User, db: Session):
        if current_user.role != "admin":
            raise PermissionDeniedException("You are not authorized to update a team")
        team=db.query(Team).filter(Team.id==id).first()
        if not team:
            raise NotFoundException(f"Team {id} not found")
        
        updated_team=team
        if team.name != team_update.name:
            existing_team=db.query(Team).filter(Team.name==team_update.name).first()
            if existing_team:
                raise AlreadyExistsException(f"Team {team_update.name} already exists")
        updated_team.name=team_update.name
        updated_team.description=team_update.description
        db.commit()
        db.refresh(updated_team)
        delete_by_prefix("teams:")
        delete_by_prefix(f"team_members:{id}:")
        return TeamResponse.model_validate(updated_team)

    def delete_team(self, id: int, current_user:User, db: Session):
        if current_user.role != "admin":
            raise PermissionDeniedException("You are not authorized to delete a team")
        team=db.query(Team).filter(Team.id==id).first()
        if not team:
            raise NotFoundException(f"Team {id} not found")
        db.delete(team)
        db.commit()
        delete_by_prefix(f"team:{id}")
        delete_by_prefix(f"team_members:{id}:")
        delete_by_prefix("teams:")
        return TeamResponse.model_validate(team)

team_service_admin=TeamServiceAdmin()