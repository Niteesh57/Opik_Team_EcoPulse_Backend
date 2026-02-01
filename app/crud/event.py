"""
CRUD operations for Event model
"""
from typing import Optional, List
from uuid import uuid4
from sqlalchemy.orm import Session
from app.models.event import Event, EventType
from app.schemas.event import EventCreate, EventUpdate
from app.crud import user_room as user_room_crud
from app.utils.image import image_request


def _generate_event_id() -> str:
    # Human-friendly event id: prefix + 8 hex chars
    return f"EVT{uuid4().hex[:8].upper()}"


def get_event_by_id(db: Session, id: int) -> Optional[Event]:
    return db.query(Event).filter(Event.id == id).first()


def get_event_by_event_id(db: Session, event_id: str) -> Optional[Event]:
    return db.query(Event).filter(Event.event_id == event_id).first()


def get_events(db: Session, skip: int = 0, limit: int = 100) -> List[Event]:
    return db.query(Event).offset(skip).limit(limit).all()


def get_events_by_room(db: Session, room_id: str, skip: int = 0, limit: int = 100) -> List[Event]:
    return db.query(Event).filter(Event.room_id == room_id).offset(skip).limit(limit).all()


def create_event(db: Session, event_in: EventCreate, user_id: int) -> Event:
    """Create an event. If room_id is omitted, use the user's first joined room.

    Raises ValueError if room cannot be determined.
    """
    event_id = _generate_event_id()

    room_id = event_in.room_id
    if not room_id:
        # Try to find a joined room for the user
        user_rooms = user_room_crud.get_user_rooms(db, user_id=user_id)
        if not user_rooms:
            raise ValueError("No room_id provided and user is not associated with any room")
        room_id = user_rooms[0].room_id

    db_event = Event(
        event_id=event_id,
        user_id=user_id,
        room_id=room_id,
        event_name=event_in.event_name,
        event_description=event_in.event_description,
        event_place=getattr(event_in, "event_place", None),
        event_date=getattr(event_in, "event_date", None),
        event_type=event_in.event_type,
        event_image_url=event_in.event_image_url,
        image_request_id=getattr(event_in, "image_request_id", None),
        tag=event_in.tag,
        event_classification=event_in.event_classification,
        # New fields
        start_time=getattr(event_in, "start_time", None),
        end_time=getattr(event_in, "end_time", None),
        max_participants=getattr(event_in, "max_participants", None),
        current_participants=0,
        guest_speakers=getattr(event_in, "guest_speakers", None),
        rsvp_link=getattr(event_in, "rsvp_link", None),
        rsvp_required=getattr(event_in, "rsvp_required", False),
        event_status=getattr(event_in, "event_status", None),
        reminder_enabled=getattr(event_in, "reminder_enabled", False),
        reminder_hours_before=getattr(event_in, "reminder_hours_before", None),
    )
    data = image_request(event_in.event_name)
    db_event.image_request_id = data

    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    
    # Auto-populate event_user with the creator
    from app.crud import event_user as event_user_crud
    event_user_crud.join_event(db, db_event, user_id)
    
    return db_event


def update_event(db: Session, event: Event, event_in: EventUpdate) -> Event:
    update_data = event_in.model_dump(exclude_unset=True) if hasattr(event_in, 'model_dump') else event_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, event: Event) -> bool:
    db.delete(event)
    db.commit()
    return True


def get_events_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Event]:
    return db.query(Event).filter(Event.user_id == user_id).offset(skip).limit(limit).all()