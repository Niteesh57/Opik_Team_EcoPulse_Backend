"""Event endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.user import User as UserModel
from app.schemas.event import EventCreate, EventOut, EventUpdate, EventUserOut, EventOutWithUserStatus
from app.crud import event as event_crud
from app.crud import event_user as event_user_crud
from app.crud import user_room as user_room_crud

router = APIRouter()


@router.post("/", response_model=EventOut, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    # Create event; room_id will be resolved from the user's joined rooms when omitted
    try:
        db_event = event_crud.create_event(db, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return db_event


@router.get("/", response_model=List[EventOutWithUserStatus])
async def list_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    room_id: Optional[str] = None,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List events from user's communities with user-specific status.
    
    Returns events only from communities the user has joined.
    Each event includes:
    - this_user_already_joined: True if the user is attending this event
    - this_user_owner: True if the user created this event
    """
    # Get all room_ids the user has joined
    user_rooms = user_room_crud.get_user_rooms(db, user_id=current_user.id)
    user_room_ids = [ur.room_id for ur in user_rooms]
    
    if not user_room_ids:
        return []  # User hasn't joined any community
    
    # If specific room_id requested, verify user is a member
    if room_id:
        if room_id not in user_room_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this community"
            )
        events = event_crud.get_events_by_room(db, room_id=room_id, skip=skip, limit=limit)
    else:
        # Get events from ALL user's communities
        events = []
        for rid in user_room_ids:
            room_events = event_crud.get_events_by_room(db, room_id=rid, skip=skip, limit=limit)
            events.extend(room_events)
        # Sort by created_at descending and apply pagination
        events = sorted(events, key=lambda e: e.created_at or e.id, reverse=True)[:limit]
    
    # Build response with user-specific fields
    result = []
    for event in events:
        # Check if user has joined this event
        is_joined = event_user_crud.is_attending(db, event, current_user.id)
        is_owner = event.user_id == current_user.id
        registered_count = event_user_crud.count_event_attendees(db, event.id)
        
        # Convert to dict and add custom fields
        event_data = EventOutWithUserStatus.from_orm(event)
        event_data.this_user_already_joined = is_joined
        event_data.this_user_owner = is_owner
        event_data.registered_users_count = registered_count
        result.append(event_data)
    
    return result


@router.get("/{event_id}", response_model=EventOut)
async def get_event(event_id: str, db: Session = Depends(get_db)):
    event = event_crud.get_event_by_event_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.post("/{event_id}/join", response_model=EventUserOut)
async def join_event(
    event_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Join an event. User can only join events in their community."""
    event = event_crud.get_event_by_event_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    
    # Check if user is a member of the event's community
    user_rooms = user_room_crud.get_user_rooms(db, user_id=current_user.id)
    user_room_ids = [ur.room_id for ur in user_rooms]
    
    if event.room_id not in user_room_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="You can only join events in your community"
        )
    
    attendee = event_user_crud.join_event(db, event, current_user.id)
    if attendee is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already joined")
    return attendee


@router.delete("/{event_id}/leave", status_code=status.HTTP_200_OK)
async def leave_event(
    event_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    event = event_crud.get_event_by_event_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    success = event_user_crud.leave_event(db, event, current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not attending")
    return {"message": "Left event"}


@router.get("/user", response_model=List[EventOut])
async def list_user_events(
    current_user: UserModel = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return event_crud.get_events_by_user(db, user_id=current_user.id, skip=skip, limit=limit)


@router.get("/{event_id}/attendees", response_model=List[EventUserOut])
async def list_event_attendees(event_id: str, db: Session = Depends(get_db)):
    event = event_crud.get_event_by_event_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    attendees = event_user_crud.get_event_attendees(db, event.id)
    return attendees


@router.put("/{event_id}", response_model=EventOut)
async def update_event_endpoint(
    event_id: str,
    payload: EventUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    event = event_crud.get_event_by_event_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to modify this event")
    updated = event_crud.update_event(db, event, payload)
    return updated


@router.delete("/{event_id}", status_code=status.HTTP_200_OK)
async def delete_event_endpoint(
    event_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    event = event_crud.get_event_by_event_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this event")
    event_crud.delete_event(db, event)
    return {"message": "Event deleted"}
