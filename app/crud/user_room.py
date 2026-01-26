"""
CRUD operations for UserRoom model
"""
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from app.models.user_room import UserRoom
from app.schemas.user_room import UserRoomCreate


def get_user_room(db: Session, user_id: int, room_id: str) -> Optional[UserRoom]:
    """Get a specific user-room relationship"""
    return db.query(UserRoom).filter(
        UserRoom.user_id == user_id,
        UserRoom.room_id == room_id
    ).first()


def get_user_rooms(db: Session, user_id: int) -> List[UserRoom]:
    """Get all rooms a user has joined"""
    return (
        db.query(UserRoom)
        .options(joinedload(UserRoom.room))
        .filter(UserRoom.user_id == user_id)
        .all()
    )


def get_room_members(db: Session, room_id: str) -> List[UserRoom]:
    """Get all users who joined a specific room"""
    return db.query(UserRoom).filter(UserRoom.room_id == room_id).all()


def join_room(db: Session, user_room: UserRoomCreate, user_id: int) -> Optional[UserRoom]:
    """Join a user to a room"""
    try:
        db_user_room = UserRoom(
            user_id=user_id,
            room_id=user_room.room_id,
            room_number=user_room.room_number
        )
        db.add(db_user_room)
        db.commit()
        db.refresh(db_user_room)
        return db_user_room
    except IntegrityError:
        db.rollback()
        return None


def leave_room(db: Session, user_id: int, room_id: str) -> bool:
    """Remove a user from a room"""
    user_room = get_user_room(db, user_id, room_id)
    if not user_room:
        return False
    
    db.delete(user_room)
    db.commit()
    return True


def update_room_number(db: Session, user_id: int, room_id: str, room_number: str) -> Optional[UserRoom]:
    """Update user's room number"""
    user_room = get_user_room(db, user_id, room_id)
    if not user_room:
        return None
    
    user_room.room_number = room_number
    db.commit()
    db.refresh(user_room)
    return user_room
