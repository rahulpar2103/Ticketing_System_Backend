from fastapi import APIRouter
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.teams import router as teams_router
from app.routers.tickets import router as tickets_router
from app.routers.comments import router as comments_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(users_router)
router.include_router(teams_router)
router.include_router(tickets_router)
router.include_router(comments_router)
