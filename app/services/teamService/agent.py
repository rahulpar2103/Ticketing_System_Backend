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

class TeamServiceAgent:
    def get_team(self, id: int, current_user:User, db: Session):
        if current_user.role != "agent":
            raise PermissionDeniedException("You are not authorized to hit this endpoint.")
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
        if current_user.role != "agent":
            raise PermissionDeniedException("You are not authorized to hit this endpoint.")
        if current_user.team_id != team_id:
            raise PermissionDeniedException("You are not authorized to get members of this team.")
        cache_key=f"team_members:{team_id}:{limit}:{offset}"
        cached_team_members=redis_client.get(cache_key)
        if cached_team_members:
            return cached_team_members
        team_members=db.query(User).filter(User.team_id==team_id).all()
        if not team_members:
            raise NotFoundException(f"Team {team_id} not found")
        redis_client.setex(cache_key,60*60*24,[UserResponse.model_validate(user) for user in team_members])
        return [UserResponse.model_validate(user) for user in team_members]

team_service_agent=TeamServiceAgent()
