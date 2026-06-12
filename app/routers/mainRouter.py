from fastapi import APIRouter
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.teams import router as teams_router
from app.routers.tickets import router as tickets_router
from app.routers.comments import router as comments_router
from app.routers.attachments import router as attachments_router
from app.routers.websocket import router as websocket_router
from app.routers.chatbot import router as chatbot_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(users_router)
router.include_router(teams_router)
router.include_router(tickets_router)
router.include_router(comments_router)
router.include_router(attachments_router)
router.include_router(websocket_router)
router.include_router(chatbot_router, prefix="/chatbot", tags=["Chatbot"])

