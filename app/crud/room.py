"""
CRUD operations for Room model
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.room import Room, generate_room_id
from app.schemas.room import RoomCreate, RoomUpdate


def get_room_by_id(db: Session, room_id: int) -> Optional[Room]:
    """Get room by database ID"""
    return db.query(Room).filter(Room.id == room_id).first()


def get_room_by_room_id(db: Session, room_id: str) -> Optional[Room]:
    """Get room by unique room_id"""
    return db.query(Room).filter(Room.room_id == room_id).first()


def get_rooms(db: Session, skip: int = 0, limit: int = 100) -> List[Room]:
    """Get list of rooms with pagination"""
    return db.query(Room).offset(skip).limit(limit).all()


def get_rooms_by_creator(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Room]:
    """Get rooms created by a specific user"""
    return db.query(Room).filter(Room.created_by == user_id).offset(skip).limit(limit).all()


def create_room(db: Session, room: RoomCreate, user_id: int) -> Room:
    """Create a new room"""
    # Generate unique room_id
    room_id = generate_room_id()
    
    # Ensure room_id is unique
    while get_room_by_room_id(db, room_id) is not None:
        room_id = generate_room_id()
    
    db_room = Room(
        room_id=room_id,
        name=room.name,
        description=room.description,
        location=room.location,
        created_by=user_id,
        doctor=room.doctor,
        shop=room.shop,
        security=room.security,
        partyhall=room.partyhall,
        cleaning=room.cleaning,
        playground=room.playground,
        staff_assignments=room.staff_assignments or {}
    )
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room


def update_room(db: Session, room_id: int, room_update: RoomUpdate) -> Optional[Room]:
    """Update a room"""
    db_room = get_room_by_id(db, room_id)
    if not db_room:
        return None
    
    update_data = room_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_room, field, value)
    
    db.commit()
    db.refresh(db_room)
    return db_room


def delete_room(db: Session, room_id: int) -> bool:
    """Delete a room"""
    db_room = get_room_by_id(db, room_id)
    if not db_room:
        return False
    
    db.delete(db_room)
    db.commit()
    return True
