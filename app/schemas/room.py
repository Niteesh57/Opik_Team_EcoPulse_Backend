"""
Room Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class StaffAssignment(BaseModel):
    """Schema for individual staff assignment"""
    user_id: int
    available_timing: str = Field(..., example="9am-10pm")
    days: str = Field(..., example="monday-friday")


class RoomBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=200)
    
    # Room type flags
    doctor: bool = False
    shop: bool = False
    security: bool = False
    partyhall: bool = False
    cleaning: bool = False
    playground: bool = False
    
    # Staff assignments
    staff_assignments: Optional[Dict[str, Dict[str, Any]]] = Field(
        None,
        example={
            "doctor": {"user_id": 1, "available_timing": "9am-10pm", "days": "monday-friday"},
            "security": {"user_id": 2, "available_timing": "9am-10pm", "days": "monday-sunday"},
            "cleaning": {"user_id": 3, "available_timing": "9am-10pm", "days": "every alternative days"},
            "shop": {"user_id": 4, "available_timing": "9am-10pm", "days": "every day"}
        }
    )


class RoomCreate(RoomBase):
    """Schema for creating a room"""
    pass


class RoomUpdate(BaseModel):
    """Schema for updating a room"""
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=200)
    doctor: Optional[bool] = None
    shop: Optional[bool] = None
    security: Optional[bool] = None
    partyhall: Optional[bool] = None
    cleaning: Optional[bool] = None
    playground: Optional[bool] = None
    staff_assignments: Optional[Dict[str, Dict[str, Any]]] = None


class RoomInDB(RoomBase):
    """Schema for room in database"""
    id: int
    room_id: str
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class Room(RoomInDB):
    """Room response schema"""
    pass


class RoomWithCreator(Room):
    """Room response with creator information"""
    creator_username: str
    creator_email: str
