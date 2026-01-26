"""User room relationship endpoints."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import user_room as user_room_crud
from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.user import User as UserModel
from app.schemas.user_room import UserRoom as UserRoomSchema
from app.schemas.user_room import UserRoomResponse


router = APIRouter()


@router.get("/my-joined-rooms", response_model=List[UserRoomSchema])
async def get_my_joined_rooms(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all rooms the current user has joined."""
    user_rooms = user_room_crud.get_user_rooms(db, user_id=current_user.id)
    return user_rooms


@router.get("/check", response_model=UserRoomResponse)
async def check_user_room(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Check if user has already joined any room."""
    user_rooms = user_room_crud.get_user_rooms(db, user_id=current_user.id)

    if not user_rooms:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You have not joined any room yet",
        )

    
    user_room = user_rooms[0]

    room = user_room.room
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )

    return UserRoomResponse(
        id=user_room.id,
        user_id=user_room.user_id,
        room_id=user_room.room_id,
        room_number=user_room.room_number,
        joined_at=user_room.joined_at,
        room_name=room.name,
        room_description=room.description,
        room_location=room.location,
    )
