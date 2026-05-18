from app.dependencies.user import get_current_user
from app.schemas.userSchema import UserResponse
from app.dependencies.db import get_db
from fastapi import APIRouter, Depends
from app.services.teamService.employee import team_service_employee
from app.schemas.teamSchema import TeamResponse

router = APIRouter(prefix="/teams/employee", tags=["Employee Teams"])

@router.get("/get/{id}", response_model=TeamResponse)
async def get_team(id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    return team_service_employee.get_team(id, current_user, db)

@router.get("/members/{team_id}", response_model=list[UserResponse])
async def get_team_members(team_id: int, current_user=Depends(get_current_user), db=Depends(get_db), limit: int=10, offset: int=0):
    return team_service_employee.get_team_members(team_id, current_user, db, limit, offset)