from app.dependencies.user import get_current_user
from app.schemas.userSchema import UserResponse
from app.dependencies.db import get_db
from fastapi import APIRouter, Depends
from app.services.teamService.agent import team_service_agent
from app.schemas.teamSchema import TeamCreate, TeamResponse

router=APIRouter(prefix="/teams/agent",tags=["Agent Teams"])

@router.get("/get/{id}", response_model=TeamResponse)
async def get_team(id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    return team_service_agent.get_team(id, current_user, db)

@router.get("/members/{team_id}", response_model=list[UserResponse])
async def get_team_members(team_id: int, current_user=Depends(get_current_user), db=Depends(get_db), limit: int=10, offset: int=0):
    return team_service_agent.get_team_members(team_id, current_user, db, limit, offset)

