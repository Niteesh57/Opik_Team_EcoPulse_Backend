"""
CRUD operations for EventUser model
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.event_user import EventUser
from app.models.event import Event
from app.crud.champion import add_points


def get_event_user(db: Session, event_id: int, user_id: int) -> Optional[EventUser]:
    return db.query(EventUser).filter(EventUser.event_id == event_id, EventUser.user_id == user_id).first()


def get_event_attendees(db: Session, event_id: int) -> List[EventUser]:
    return db.query(EventUser).filter(EventUser.event_id == event_id).all()


def join_event(db: Session, event: Event, user_id: int) -> Optional[EventUser]:
    existing = get_event_user(db, event.id, user_id)
    if existing:
        return None
    eu = EventUser(event_id=event.id, user_id=user_id)
    db.add(eu)
    db.commit()
    add_points(db, user_id, 100)
    db.refresh(eu)
    return eu


def leave_event(db: Session, event: Event, user_id: int) -> bool:
    eu = get_event_user(db, event.id, user_id)
    add_points(db, user_id, -100)
    if not eu:
        return False
    db.delete(eu)
    db.commit()
    return True


def is_attending(db: Session, event: Event, user_id: int) -> bool:
    return get_event_user(db, event.id, user_id) is not None


def count_event_attendees(db: Session, event_id: int) -> int:
    """Count the number of users registered for an event."""
    return db.query(EventUser).filter(EventUser.event_id == event_id).count()