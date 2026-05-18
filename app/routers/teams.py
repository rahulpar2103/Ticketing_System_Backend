from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.limiter import limiter
from app.dependencies.db import get_db
from app.dependencies.user import get_current_user
from app.models.userModel import User, UserRole
from app.schemas.teamSchema import TeamCreate, TeamUpdate, TeamResponse
from app.schemas.userSchema import UserResponse
from app.services.teamService.admin import team_service_admin
from app.services.teamService.agent import team_service_agent
from app.services.teamService.employee import team_service_employee

router = APIRouter(prefix="/teams", tags=["Teams"])


def _get_team_service(role: UserRole):
    """Return the appropriate team service based on the user's role."""
    services = {
        UserRole.admin: team_service_admin,
        UserRole.agent: team_service_agent,
        UserRole.employee: team_service_employee,
    }
    return services[role]


@router.post("", status_code=201, response_model=TeamResponse)
@limiter.limit("20/minute")
def create_team(
    request: Request,
    team: TeamCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new team. Admin only."""
    return team_service_admin.create_team(team, current_user, db)


@router.get("", response_model=list[TeamResponse])
@limiter.limit("30/minute")
def get_all_teams(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10,
    offset: int = 0,
):
    """List all teams. Admin only."""
    return team_service_admin.get_all_teams(current_user, db, limit, offset)


@router.get("/{team_id}", response_model=TeamResponse)
@limiter.limit("30/minute")
def get_team(
    request: Request,
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a team by ID. Behavior varies by role."""
    service = _get_team_service(current_user.role)
    return service.get_team(team_id, current_user, db)


@router.put("/{team_id}", response_model=dict)
@limiter.limit("20/minute")
def update_team(
    request: Request,
    team_id: int,
    team: TeamUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a team. Admin only."""
    return team_service_admin.update_team(team_id, team, current_user, db)


@router.delete("/{team_id}", response_model=dict)
@limiter.limit("20/minute")
def delete_team(
    request: Request,
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft-delete a team. Admin only."""
    return team_service_admin.delete_team(team_id, current_user, db)


@router.get("/{team_id}/members", response_model=list[UserResponse])
@limiter.limit("30/minute")
def get_team_members(
    request: Request,
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10,
    offset: int = 0,
):
    """Get members of a team. Behavior varies by role."""
    service = _get_team_service(current_user.role)
    return service.get_team_members(team_id, current_user, db, limit, offset)
