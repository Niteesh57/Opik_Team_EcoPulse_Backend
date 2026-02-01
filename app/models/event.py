"""
Event database model - tracks community and social events
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, Time, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class EventType(str, enum.Enum):
    """Event type classification"""
    PUBLIC = "public"
    PRIVATE = "private"
    COMMUNITY = "community"
    SOCIAL = "social"


class EventStatus(str, enum.Enum):
    """Event status"""
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_id = Column(String, ForeignKey("rooms.room_id"), nullable=False)
    event_name = Column(String, nullable=False)
    event_description = Column(Text, nullable=True)
    event_place = Column(String, nullable=True)
    event_date = Column(DateTime(timezone=True), nullable=True)
    event_type = Column(Enum(EventType), nullable=False, default=EventType.PUBLIC)
    event_image_url = Column(Text, nullable=True)
    tag = Column(String, nullable=True)
    event_classification = Column(Text, nullable=True)
    
    # Time management
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    
    # Participant tracking
    max_participants = Column(Integer, nullable=True)
    current_participants = Column(Integer, default=0, nullable=False)
    
    # Additional details
    guest_speakers = Column(Text, nullable=True)
    rsvp_link = Column(String, nullable=True)
    rsvp_required = Column(Boolean, default=False, nullable=False)

    # Additional info
    notes = Column(Text, nullable=True)  # Dietary restrictions, special requests, etc.
    
    # Event status
    event_status = Column(Enum(EventStatus), nullable=False, default=EventStatus.DRAFT)
    
    # Reminders
    reminder_enabled = Column(Boolean, default=False, nullable=False)
    reminder_hours_before = Column(Integer, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    image_request_id = Column(String, nullable=True)
    
    # Relationships
    creator = relationship("User", backref="created_events", foreign_keys=[user_id])
    room = relationship("Room", backref="events", foreign_keys=[room_id])
    attendees = relationship("EventUser", back_populates="event", cascade="all, delete-orphan")
