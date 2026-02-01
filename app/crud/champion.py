"""
CRUD operations for Champion model
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.champion import Champion
from app.models.user import User
from app.models.user_room import UserRoom
from app.schemas.champion import ChampionCreate, ChampionUpdate


def get_champion_by_user_id(db: Session, user_id: int) -> Optional[Champion]:
    return db.query(Champion).filter(Champion.user_id == user_id).first()


def create_champion(db: Session, champion_in: ChampionCreate) -> Champion:
    db_champion = Champion(
        user_id=champion_in.user_id,
        points=champion_in.points
    )
    db.add(db_champion)
    db.commit()
    db.refresh(db_champion)
    return db_champion


def update_champion_points(db: Session, champion: Champion, points: int) -> Champion:
    champion.points = points
    db.commit()
    db.refresh(champion)
    return champion


def add_points(db: Session, user_id: int, points_to_add: int) -> Champion:
    champion = get_champion_by_user_id(db, user_id)
    if not champion:
        champion = create_champion(db, ChampionCreate(user_id=user_id, points=0))
    
    champion.points += points_to_add
    db.commit()
    db.refresh(champion)
    return champion


def get_leaderboard(db: Session, room_id: Optional[str] = None, skip: int = 0, limit: int = 10) -> List[Champion]:
    query = db.query(Champion)
    
    if room_id:
        query = query.join(User).join(UserRoom).filter(UserRoom.room_id == room_id)
        
    return query.order_by(desc(Champion.points)).offset(skip).limit(limit).all()
