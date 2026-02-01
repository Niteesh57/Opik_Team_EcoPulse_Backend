"""
Pydantic schemas for EventMessage
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class EventMessageBase(BaseModel):
    message: str


class EventMessageCreate(EventMessageBase):
    pass


class EventMessageOut(EventMessageBase):
    id: int
    event_id: int
    user_id: int
    created_at: datetime
    
    # Optional: include basic user info if needed for UI
    username: Optional[str] = None
    full_name: Optional[str] = None

    class Config:
        from_attributes = True
