"""
Pydantic schemas for Notifications
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class NotificationBase(BaseModel):
    message: str
    value: Optional[int] = 0


class NotificationCreate(NotificationBase):
    to_user_id: Optional[int] = None


class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None
    value: Optional[int] = None


class NotificationOut(NotificationBase):
    id: int
    from_user_id: Optional[int] = None
    to_user_id: Optional[int] = None
    is_read: bool
    created_at: datetime
    
    # Optional sender info
    from_username: Optional[str] = None

    class Config:
        from_attributes = True
