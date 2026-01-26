"""API v1 router configuration."""
from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.rooms import router as rooms_router
from app.api.v1.endpoints.user_room import router as user_room_router
from app.api.v1.endpoints.user_message import router as user_message_router
from app.api.v1.endpoints.users import router as users_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(user_room_router, prefix="/rooms", tags=["User Rooms"])
api_router.include_router(user_message_router, prefix="/chat", tags=["Chat"])
api_router.include_router(rooms_router, prefix="/rooms", tags=["Rooms"])
