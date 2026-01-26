"""
UserRoom Pydantic schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserRoomBase(BaseModel):
    room_id: str = Field(..., description="Unique room ID to join")
    room_number: Optional[str] = Field(None, max_length=50, description="User's room/unit number")


class UserRoomCreate(UserRoomBase):
    """Schema for joining a room"""
    pass


class UserRoomInDB(UserRoomBase):
    """Schema for user room in database"""
    id: int
    user_id: int
    joined_at: datetime
    
    class Config:
        from_attributes = True


class UserRoomResponse(BaseModel):
    """Response schema when joining a room"""
    id: int
    user_id: int
    room_id: str
    room_number: Optional[str]
    joined_at: datetime
    
    # Room details
    room_name: str
    room_description: Optional[str]
    room_location: Optional[str]
    
    class Config:
        from_attributes = True


class UserRoom(UserRoomInDB):
    """User room schema"""
    pass
