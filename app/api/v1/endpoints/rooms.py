"""Room management endpoints."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.room import Room, RoomCreate, RoomUpdate, RoomWithCreator
from app.schemas.user_room import (
    UserRoomCreate,
    UserRoomResponse,
    UserRoom as UserRoomSchema,
)
from app.crud import room as room_crud
from app.crud import user_room as user_room_crud
from app.dependencies import get_current_superuser, get_current_active_user
from app.models.user import User as UserModel


router = APIRouter()


@router.post("/", response_model=Room, status_code=status.HTTP_201_CREATED)
async def create_room(
    room: RoomCreate,
    current_user: UserModel = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """Create a new room (Admin only)."""
    new_room = room_crud.create_room(db=db, room=room, user_id=current_user.id)
    return new_room


@router.get("/", response_model=List[Room])
async def get_all_rooms(
    skip: int = 0,
    limit: int = 100,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all rooms."""
    rooms = room_crud.get_rooms(db, skip=skip, limit=limit)
    return rooms


@router.get("/my-rooms", response_model=List[Room])
async def get_my_rooms(
    skip: int = 0,
    limit: int = 100,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get rooms created by current user."""
    rooms = room_crud.get_rooms_by_creator(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return rooms


@router.get("/{room_id}", response_model=Room)
async def get_room_by_room_id(
    room_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get room details by room_id."""
    room = room_crud.get_room_by_room_id(db, room_id=room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )
    return room


@router.put("/{room_id}", response_model=Room)
async def update_room(
    room_id: str,
    room_update: RoomUpdate,
    current_user: UserModel = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """Update room details (Admin only)."""
    room = room_crud.get_room_by_room_id(db, room_id=room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )

    updated_room = room_crud.update_room(db, room_id=room.id, room_update=room_update)
    return updated_room


@router.delete("/{room_id}", status_code=status.HTTP_200_OK)
async def delete_room(
    room_id: str,
    current_user: UserModel = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """Delete a room (Admin only)."""
    room = room_crud.get_room_by_room_id(db, room_id=room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )

    success = room_crud.delete_room(db, room_id=room.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete room",
        )

    return {"message": "Room deleted successfully"}


@router.post("/join", response_model=UserRoomResponse, status_code=status.HTTP_201_CREATED)
async def join_room(
    user_room: UserRoomCreate,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Join a room using room_id."""
    room = room_crud.get_room_by_room_id(db, room_id=user_room.room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )

    existing = user_room_crud.get_user_room(
        db, user_id=current_user.id, room_id=user_room.room_id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already joined this room",
        )

    joined = user_room_crud.join_room(db=db, user_room=user_room, user_id=current_user.id)
    if not joined:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to join room",
        )

    return UserRoomResponse(
        id=joined.id,
        user_id=joined.user_id,
        room_id=joined.room_id,
        room_number=joined.room_number,
        joined_at=joined.joined_at,
        room_name=room.name,
        room_description=room.description,
        room_location=room.location,
    )


@router.delete("/leave/{room_id}", status_code=status.HTTP_200_OK)
async def leave_room(
    room_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Leave a room."""
    success = user_room_crud.leave_room(
        db, user_id=current_user.id, room_id=room_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a member of this room",
        )

    return {"message": "Successfully left the room"}
