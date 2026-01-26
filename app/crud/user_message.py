"""CRUD helpers for chat sessions and messages."""
from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.message import MessageSession, UserMessage
from app.schemas.user_message import MessageSessionCreate, UserMessageCreate


def create_session(db: Session, payload: MessageSessionCreate) -> Optional[MessageSession]:
    session = MessageSession(
        user_id=payload.user_id,
        first_user_message=payload.first_user_message,
    )
    if payload.session_id:
        session.session_id = payload.session_id
    try:
        db.add(session)
        db.commit()
        db.refresh(session)
        return session
    except IntegrityError:
        db.rollback()
        return None


def get_session(db: Session, session_id: str) -> Optional[MessageSession]:
    return (
        db.query(MessageSession)
        .filter(MessageSession.session_id == session_id)
        .first()
    )


def get_user_sessions(db: Session, user_id: int, skip: int = 0, limit: int = 20) -> List[MessageSession]:
    return (
        db.query(MessageSession)
        .filter(MessageSession.user_id == user_id)
        .order_by(MessageSession.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_message(db: Session, message_id: int) -> Optional[UserMessage]:
    return db.query(UserMessage).filter(UserMessage.id == message_id).first()


def create_user_message(db: Session, payload: UserMessageCreate) -> Optional[UserMessage]:
    if not payload.user_message and not payload.ai_message:
        return None
    message = UserMessage(
        session_id=payload.session_id,
        user_id=payload.user_id,
        role=payload.role,
        user_message=payload.user_message,
        ai_message=payload.ai_message,
        liked=payload.liked,
        disliked=payload.disliked,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_session_messages(db: Session, session_id: str) -> List[UserMessage]:
    return (
        db.query(UserMessage)
        .filter(UserMessage.session_id == session_id)
        .order_by(UserMessage.created_at.asc())
        .all()
    )


def set_feedback(db: Session, message_id: int, liked: Optional[bool], disliked: Optional[bool]) -> Optional[UserMessage]:
    message = get_message(db, message_id)
    if not message:
        return None
    message.liked = liked
    message.disliked = disliked
    db.commit()
    db.refresh(message)
    return message


def update_ai_message(db: Session, message_id: int, ai_message: str) -> Optional[UserMessage]:
    message = get_message(db, message_id)
    if not message:
        return None
    message.ai_message = ai_message
    db.commit()
    db.refresh(message)
    return message


def delete_session(db: Session, session_id: str, user_id: int) -> bool:
    session = (
        db.query(MessageSession)
        .filter(MessageSession.session_id == session_id, MessageSession.user_id == user_id)
        .first()
    )
    if not session:
        return False
    db.delete(session)
    db.commit()
    return True
