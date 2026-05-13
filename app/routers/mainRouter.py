# pyrefly: ignore [missing-import]
from fastapi import APIRouter
from app.routers.userRouters.auth import router as auth
from app.routers.userRouters.admin import router as admin
# from app.routers.userRouters.agent import router as agent
# from app.routers.userRouters.employee import router as employee

router = APIRouter(prefix="/users", tags=["Users"])

router.include_router(auth)
router.include_router(admin)
# router.include_router(agent)
# router.include_router(employee)