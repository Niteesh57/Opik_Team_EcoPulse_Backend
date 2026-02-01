"""
Pydantic schemas for NearPeople
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class NearPeopleCreate(BaseModel):
    """Schema for adding a new near person"""
    near_user_id: int
    nickname: Optional[str] = None
    notes: Optional[str] = None


class NearPeopleUpdate(BaseModel):
    """Schema for updating near person details"""
    nickname: Optional[str] = None
    notes: Optional[str] = None


class UserBasicInfo(BaseModel):
    """Basic user info for search results and near people list"""
    id: int
    username: str
    full_name: Optional[str] = None
    email: str
    
    class Config:
        from_attributes = True


class NearPeopleOut(BaseModel):
    """Schema for returning near person details"""
    id: int
    user_id: int
    near_user_id: int
    room_id: str
    nickname: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    near_user: UserBasicInfo
    
    class Config:
        from_attributes = True


class UserSearchResult(BaseModel):
    """Schema for user search results"""
    id: int
    username: str
    full_name: Optional[str] = None
    email: str
    room_number: Optional[str] = None  # Their unit/room number in the community
    is_already_added: bool = False  # Whether already in user's near people list
    
    class Config:
        from_attributes = True
