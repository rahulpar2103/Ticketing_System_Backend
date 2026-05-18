from app.schemas.teamSchema import TeamUpdate
from app.models import teamModel
from app.dependencies.user import get_current_user
from app.schemas.userSchema import UserResponse
from app.dependencies.db import get_db
from fastapi import APIRouter, Depends
from app.services.teamService.admin import team_service_admin
from app.schemas.teamSchema import TeamCreate, TeamResponse

router = APIRouter(prefix="/teams/admin", tags=["Admin Teams"])

@router.post("/create", status_code=201, response_model=TeamResponse)
def create_team(team: TeamCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    return team_service_admin.create_team(team, current_user, db)

@router.get('/get-all', response_model=list[TeamResponse])
def get_all_teams(current_user=Depends(get_current_user), db=Depends(get_db), limit: int=10, offset: int=0):
    return team_service_admin.get_all_teams(current_user, db, limit, offset)

@router.get('/members/{team_id}', response_model=list[UserResponse])
def get_team_members(team_id: int, current_user=Depends(get_current_user), db=Depends(get_db), limit: int=10, offset: int=0):
    return team_service_admin.get_team_members(team_id, current_user, db, limit, offset)
    
@router.get('/{id}', response_model=TeamResponse)
def get_team(id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    return team_service_admin.get_team(id, current_user, db)

@router.put('/update/{id}', response_model=dict)
def update_team(id: int, team: TeamUpdate, current_user=Depends(get_current_user), db=Depends(get_db)):
    return team_service_admin.update_team(id, team, current_user, db)

@router.delete('/delete/{id}', response_model=dict)
def delete_team(id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    return team_service_admin.delete_team(id, current_user, db)