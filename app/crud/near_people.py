"""
CRUD operations for NearPeople model
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.near_people import NearPeople
from app.models.user import User
from app.models.user_room import UserRoom
from app.schemas.near_people import NearPeopleCreate, NearPeopleUpdate


def get_near_people(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[NearPeople]:
    """Get all near people for a user"""
    return (
        db.query(NearPeople)
        .filter(NearPeople.user_id == user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_near_person_by_id(db: Session, near_person_id: int) -> Optional[NearPeople]:
    """Get a specific near person entry by ID"""
    return db.query(NearPeople).filter(NearPeople.id == near_person_id).first()


def get_near_person_by_users(db: Session, user_id: int, near_user_id: int) -> Optional[NearPeople]:
    """Check if a near person connection already exists"""
    return (
        db.query(NearPeople)
        .filter(NearPeople.user_id == user_id, NearPeople.near_user_id == near_user_id)
        .first()
    )


def add_near_person(
    db: Session, 
    user_id: int, 
    near_person_in: NearPeopleCreate,
    room_id: str
) -> NearPeople:
    """Add a user as near person"""
    db_near_person = NearPeople(
        user_id=user_id,
        near_user_id=near_person_in.near_user_id,
        room_id=room_id,
        nickname=near_person_in.nickname,
        notes=near_person_in.notes,
    )
    db.add(db_near_person)
    db.commit()
    db.refresh(db_near_person)
    return db_near_person


def update_near_person(
    db: Session, 
    near_person: NearPeople, 
    near_person_in: NearPeopleUpdate
) -> NearPeople:
    """Update near person nickname/notes"""
    update_data = near_person_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(near_person, field, value)
    db.commit()
    db.refresh(near_person)
    return near_person


def remove_near_person(db: Session, near_person: NearPeople) -> bool:
    """Remove a near person connection"""
    db.delete(near_person)
    db.commit()
    return True


def search_room_members(
    db: Session, 
    user_id: int, 
    room_id: str, 
    query: str,
    skip: int = 0,
    limit: int = 20
) -> List[dict]:
    """
    Search for users in the same room by username, full_name, or email.
    Returns users with their room numbers and whether they're already added.
    """
    # Get IDs of users already in near people list
    existing_near_ids = (
        db.query(NearPeople.near_user_id)
        .filter(NearPeople.user_id == user_id)
        .all()
    )
    existing_ids = {row[0] for row in existing_near_ids}
    
    # Search for users in the same room (exclude admins)
    search_pattern = f"%{query}%"
    results = (
        db.query(User, UserRoom.room_number)
        .join(UserRoom, User.id == UserRoom.user_id)
        .filter(
            UserRoom.room_id == room_id,
            User.id != user_id,  # Exclude the current user
            User.is_active == True,
            User.is_superuser == False,  # Exclude admins
            or_(
                User.username.ilike(search_pattern),
                User.full_name.ilike(search_pattern),
                User.email.ilike(search_pattern),
            )
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    # Format results
    return [
        {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "room_number": room_number,
            "is_already_added": user.id in existing_ids,
        }
        for user, room_number in results
    ]


def get_room_members(
    db: Session, 
    user_id: int, 
    room_id: str,
    skip: int = 0,
    limit: int = 50
) -> List[dict]:
    """
    Get all members in the same room (for browsing without search).
    """
    # Get IDs of users already in near people list
    existing_near_ids = (
        db.query(NearPeople.near_user_id)
        .filter(NearPeople.user_id == user_id)
        .all()
    )
    existing_ids = {row[0] for row in existing_near_ids}
    
    # Get all users in the same room (exclude admins)
    results = (
        db.query(User, UserRoom.room_number)
        .join(UserRoom, User.id == UserRoom.user_id)
        .filter(
            UserRoom.room_id == room_id,
            User.id != user_id,  # Exclude the current user
            User.is_active == True,
            User.is_superuser == False,  # Exclude admins
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    # Format results
    return [
        {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "room_number": room_number,
            "is_already_added": user.id in existing_ids,
        }
        for user, room_number in results
    ]
