"""
Pydantic schemas for Champions
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ChampionBase(BaseModel):
    points: int = 0


class ChampionCreate(ChampionBase):
    user_id: int


class ChampionUpdate(BaseModel):
    points: Optional[int] = None


class ChampionOut(ChampionBase):
    id: int
    user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ChampionLeaderboardEntry(ChampionOut):
    username: str
    full_name: Optional[str] = None
    
    class Config:
        from_attributes = True
