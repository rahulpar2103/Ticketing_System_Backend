from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session
from app.core.limiter import limiter
from app.dependencies.db import get_db
from app.dependencies.user import get_current_user
from app.models.userModel import User, UserRole
from app.schemas.teamSchema import TeamCreate, TeamUpdate, TeamResponse
from app.schemas.userSchema import UserResponse
from app.schemas.pagination import PaginatedResponse
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


@router.get("", response_model=PaginatedResponse[TeamResponse])
@limiter.limit("30/minute")
def get_all_teams(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at", description="Sort field: created_at, updated_at, name"),
    order: str = Query("desc", description="Sort order: asc or desc"),
):
    """List all teams with sorting. Admin only."""
    return team_service_admin.get_all_teams(current_user, db, limit, offset, sort_by, order)


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


@router.patch("/{team_id}/reactivate", response_model=dict)
@limiter.limit("20/minute")
def reactivate_team(
    request: Request,
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Re-enable a soft-deleted team. Admin only."""
    return team_service_admin.reactivate_team(team_id, current_user, db)


@router.get("/{team_id}/stats", response_model=dict)
@limiter.limit("30/minute")
def get_team_stats(
    request: Request,
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get per-team ticket statistics. Admin only."""
    return team_service_admin.get_team_stats(team_id, current_user, db)


@router.get("/{team_id}/members", response_model=PaginatedResponse[UserResponse])
@limiter.limit("30/minute")
def get_team_members(
    request: Request,
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at", description="Sort field: created_at, name, username"),
    order: str = Query("desc", description="Sort order: asc or desc"),
):
    """Get members of a team with sorting. Behavior varies by role."""
    service = _get_team_service(current_user.role)
    return service.get_team_members(team_id, current_user, db, limit, offset, sort_by, order)
