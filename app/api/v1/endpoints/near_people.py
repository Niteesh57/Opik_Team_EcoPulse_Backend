"""
API endpoints for Near People functionality
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.crud import near_people as near_people_crud
from app.crud import user_room as user_room_crud
from app.crud import user as user_crud
from app.schemas.near_people import (
    NearPeopleCreate,
    NearPeopleUpdate,
    NearPeopleOut,
    UserSearchResult,
)
from app.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/near-people", tags=["near-people"])


@router.get("/", response_model=List[NearPeopleOut])
def get_my_near_people(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get all near people for the current user"""
    near_people = near_people_crud.get_near_people(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return near_people


@router.get("/search", response_model=List[UserSearchResult])
def search_room_members(
    q: str = Query(..., min_length=1, description="Search query"),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Search for users in the same community by name or email"""
    # Get the user's room_id
    user_rooms = user_room_crud.get_user_rooms(db, user_id=current_user.id)
    if not user_rooms:
        raise HTTPException(status_code=400, detail="You are not part of any community")
    
    # Use the first room (or you could allow selecting a specific room)
    room_id = user_rooms[0].room_id
    
    results = near_people_crud.search_room_members(
        db, user_id=current_user.id, room_id=room_id, query=q, skip=skip, limit=limit
    )
    return results


@router.get("/members", response_model=List[UserSearchResult])
def get_all_room_members(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get all members in the same community (for browsing)"""
    # Get the user's room_id
    user_rooms = user_room_crud.get_user_rooms(db, user_id=current_user.id)
    if not user_rooms:
        raise HTTPException(status_code=400, detail="You are not part of any community")
    
    room_id = user_rooms[0].room_id
    
    results = near_people_crud.get_room_members(
        db, user_id=current_user.id, room_id=room_id, skip=skip, limit=limit
    )
    return results


@router.post("/add", response_model=NearPeopleOut)
def add_near_person(
    near_person_in: NearPeopleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Add a user as near person (neighbor)"""
    # Cannot add yourself
    if near_person_in.near_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot add yourself as a near person")
    
    # Check if the user exists
    target_user = user_crud.get_user_by_id(db, near_person_in.near_user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Admins cannot be added as neighbors
    if target_user.is_superuser:
        raise HTTPException(status_code=400, detail="Admin users cannot be added as neighbors")
    
    # Get the current user's room_id
    user_rooms = user_room_crud.get_user_rooms(db, user_id=current_user.id)
    if not user_rooms:
        raise HTTPException(status_code=400, detail="You are not part of any community")
    
    room_id = user_rooms[0].room_id
    
    # Check if the target user is in the same room
    target_user_rooms = user_room_crud.get_user_rooms(db, user_id=near_person_in.near_user_id)
    if not any(ur.room_id == room_id for ur in target_user_rooms):
        raise HTTPException(
            status_code=400, 
            detail="You can only add users from your own community"
        )
    
    # Check if already added
    existing = near_people_crud.get_near_person_by_users(
        db, user_id=current_user.id, near_user_id=near_person_in.near_user_id
    )
    if existing:
        raise HTTPException(status_code=400, detail="This user is already in your near people list")
    
    # Add the near person
    near_person = near_people_crud.add_near_person(
        db, user_id=current_user.id, near_person_in=near_person_in, room_id=room_id
    )
    return near_person


@router.put("/{near_person_id}", response_model=NearPeopleOut)
def update_near_person(
    near_person_id: int,
    near_person_in: NearPeopleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update near person nickname or notes"""
    near_person = near_people_crud.get_near_person_by_id(db, near_person_id)
    
    if not near_person:
        raise HTTPException(status_code=404, detail="Near person not found")
    
    if near_person.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this entry")
    
    updated = near_people_crud.update_near_person(db, near_person, near_person_in)
    return updated


@router.delete("/{near_person_id}")
def remove_near_person(
    near_person_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Remove a user from near people list"""
    near_person = near_people_crud.get_near_person_by_id(db, near_person_id)
    
    if not near_person:
        raise HTTPException(status_code=404, detail="Near person not found")
    
    if near_person.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to remove this entry")
    
    near_people_crud.remove_near_person(db, near_person)
    return {"message": "Near person removed successfully"}
