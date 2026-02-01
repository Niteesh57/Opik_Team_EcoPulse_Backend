from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, time
from enum import Enum


class EventType(str, Enum):
    public = "public"
    private = "private"
    community = "community"
    social = "social"


class EventStatus(str, Enum):
    draft = "draft"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class EventBase(BaseModel):
    event_name: str = Field(..., min_length=1)
    event_description: Optional[str] = None
    event_place: Optional[str] = None
    event_date: Optional[datetime] = None
    event_type: EventType = EventType.public
    event_image_url: Optional[str] = None
    image_request_id: Optional[str] = None  # For tracking async image generation
    tag: Optional[str] = None
    event_classification: Optional[str] = None
    room_id: Optional[str] = None  # If omitted, resolved from user's joined communities
    
    # Time management
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    
    # Participant tracking
    max_participants: Optional[int] = None
    
    # Additional details
    guest_speakers: Optional[str] = None
    rsvp_link: Optional[str] = None
    rsvp_required: bool = False
    
    # Event status
    event_status: EventStatus = EventStatus.draft
    
    # Reminders
    reminder_enabled: bool = False
    reminder_hours_before: Optional[int] = None


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    event_name: Optional[str] = None
    event_description: Optional[str] = None
    event_place: Optional[str] = None
    event_date: Optional[datetime] = None
    event_type: Optional[EventType] = None
    event_image_url: Optional[str] = None
    image_request_id: Optional[str] = None
    tag: Optional[str] = None
    event_classification: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    max_participants: Optional[int] = None
    guest_speakers: Optional[str] = None
    rsvp_link: Optional[str] = None
    rsvp_required: Optional[bool] = None
    event_status: Optional[EventStatus] = None
    reminder_enabled: Optional[bool] = None
    reminder_hours_before: Optional[int] = None


class EventOut(EventBase):
    id: int
    event_id: str
    user_id: int
    current_participants: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EventOutWithUserStatus(EventOut):
    """Extended event response with user-specific status fields."""
    this_user_already_joined: bool = False
    this_user_owner: bool = False
    registered_users_count: int = 0  # Number of users who joined the event

    class Config:
        from_attributes = True


class EventUserCreate(BaseModel):
    # Minimal join payload
    pass


class EventUserOut(BaseModel):
    id: int
    event_id: int
    user_id: int
    joined_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True