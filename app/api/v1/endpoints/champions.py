"""
API endpoints for Champions (Leaderboard)
"""
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.v1.endpoints import events
from app.crud import champion as champion_crud
from app.schemas.champion import ChampionOut, ChampionLeaderboardEntry, ChampionCreate
from app.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/champions", tags=["champions"])


@router.get("/", response_model=List[ChampionLeaderboardEntry])
async def get_leaderboard(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get the champions leaderboard for the user's community.
    """
    # Get user's room to filter leaderboard
    from app.crud import user_room as user_room_crud
    user_rooms = user_room_crud.get_user_rooms(db, user_id=current_user.id)
    
    room_id = None
    if user_rooms:
        room_id = user_rooms[0].room_id
        
    champions = champion_crud.get_leaderboard(db, room_id=room_id, skip=skip, limit=limit)
    
    # Enrich with user details
    result = []
    for champ in champions:
        champ_data = ChampionOut.from_orm(champ)
        entry = ChampionLeaderboardEntry(
            **champ_data.dict(),
            username=champ.user.username,
            full_name=champ.user.full_name
        )
        result.append(entry)
        
    return result


@router.get("/me", response_model=ChampionLeaderboardEntry)
async def get_my_champion_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get current user's champion stats.
    """
    champ = champion_crud.get_champion_by_user_id(db, current_user.id)
    if not champ:
        # Create default entry if not exists
        champ = champion_crud.create_champion(db, ChampionCreate(user_id=current_user.id, points=0))
    
    champ_data = ChampionOut.from_orm(champ)
    return ChampionLeaderboardEntry(
        **champ_data.dict(),
        username=current_user.username,
        full_name=current_user.full_name
    )
