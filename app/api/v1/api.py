"""API v1 router configuration."""
from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.rooms import router as rooms_router
from app.api.v1.endpoints.user_room import router as user_room_router
from app.api.v1.endpoints.user_message import router as user_message_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.events import router as events_router
from app.api.v1.endpoints.near_people import router as near_people_router
from app.api.v1.endpoints.champions import router as champions_router
from app.api.v1.endpoints.event_messages import router as event_messages_router
from app.api.v1.endpoints.webhooks import router as webhooks_router
from app.api.v1.endpoints.notifications import router as notifications_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(user_room_router, prefix="/rooms", tags=["User Rooms"])
api_router.include_router(user_message_router, prefix="/chat", tags=["Chat"])
api_router.include_router(rooms_router, prefix="/rooms", tags=["Rooms"])
api_router.include_router(events_router, prefix="/events", tags=["Events"])
api_router.include_router(near_people_router, tags=["Near People"])
api_router.include_router(champions_router, tags=["Champions"])
api_router.include_router(event_messages_router, tags=["Event Messages"])
api_router.include_router(notifications_router, tags=["Notifications"])
api_router.include_router(webhooks_router, prefix="/webhooks", tags=["Webhooks"])

