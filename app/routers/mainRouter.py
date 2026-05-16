# pyrefly: ignore [missing-import]
from fastapi import APIRouter
from app.routers.userRouters.auth import router as auth
from app.routers.userRouters.admin import router as user_admin
from app.routers.userRouters.agent import router as user_agent
from app.routers.userRouters.employee import router as user_employee
from app.routers.teamRouters.admin import router as team_admin
from app.routers.teamRouters.agent import router as team_agent
from app.routers.teamRouters.employee import router as team_employee
from app.routers.ticketRouters.admin import router as ticket_admin
from app.routers.ticketRouters.agent import router as ticket_agent
from app.routers.ticketRouters.employee import router as ticket_employee
from app.routers.commentRouters.admin import router as comment_admin
from app.routers.commentRouters.agent import router as comment_agent
from app.routers.commentRouters.employee import router as comment_employee

router = APIRouter(tags=["Main"])

router.include_router(auth)
router.include_router(user_admin)
router.include_router(user_agent)
router.include_router(user_employee)
router.include_router(team_admin)
router.include_router(team_agent)
router.include_router(team_employee)
router.include_router(ticket_admin)
router.include_router(ticket_agent)
router.include_router(ticket_employee)
router.include_router(comment_admin)
router.include_router(comment_agent)
router.include_router(comment_employee)
