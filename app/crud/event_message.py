"""
CRUD operations for EventMessage model
"""
from typing import List
from sqlalchemy.orm import Session
from app.models.event_message import EventMessage
from app.schemas.event_message import EventMessageCreate


def create_message(db: Session, message_in: EventMessageCreate, user_id: int, event_id: int) -> EventMessage:
    db_message = EventMessage(
        event_id=event_id,
        user_id=user_id,
        message=message_in.message
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message


from sqlalchemy import desc

def get_event_messages(db: Session, event_id: int, skip: int = 0, limit: int = 50) -> List[EventMessage]:
    # Fetch latest messages (e.g. last 50)
    messages = (
        db.query(EventMessage)
        .filter(EventMessage.event_id == event_id)
        .order_by(desc(EventMessage.created_at))  # Newest first
        .offset(skip)
        .limit(limit)
        .all()
    )
    # Reverse to return them in chronological order (oldest to newest) for client display
    return list(reversed(messages))
