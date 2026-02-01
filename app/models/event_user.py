"""
EventUser database model - tracks which users are attending which events
"""
from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint, String, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class EventUser(Base):
    __tablename__ = "event_users"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    event = relationship("Event", back_populates="attendees")
    user = relationship("User", backref="attending_events")
    
    # Ensure a user can only join an event once
    __table_args__ = (
        UniqueConstraint('event_id', 'user_id', name='unique_event_user'),
    )
