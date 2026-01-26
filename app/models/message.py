"""Models for chat message sessions and history."""
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


def generate_session_id() -> str:
    return uuid.uuid4().hex


class MessageSession(Base):
    __tablename__ = "message_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, index=True, nullable=False, default=generate_session_id)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    first_user_message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="message_sessions")
    messages = relationship(
        "UserMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        primaryjoin="MessageSession.session_id == UserMessage.session_id",
    )


class UserMessage(Base):
    __tablename__ = "user_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), ForeignKey("message_sessions.session_id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(16), nullable=False, default="user")
    user_message = Column(Text, nullable=True)
    ai_message = Column(Text, nullable=True)
    liked = Column(Boolean, nullable=True)
    disliked = Column(Boolean, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship(
        "MessageSession",
        back_populates="messages",
        primaryjoin="UserMessage.session_id == MessageSession.session_id",
        foreign_keys=[session_id],
    )
    user = relationship("User", backref="messages")
