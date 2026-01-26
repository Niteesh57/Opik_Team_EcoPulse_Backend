"""
UserRoom database model - tracks which users have joined which rooms
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class UserRoom(Base):
    __tablename__ = "user_rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_id = Column(String, ForeignKey("rooms.room_id"), nullable=False)
    room_number = Column(String, nullable=True)  # User's room/unit number
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", backref="user_rooms")
    room = relationship("Room", backref="members", foreign_keys=[room_id], primaryjoin="UserRoom.room_id == Room.room_id")
    
    # Ensure a user can only join a room once
    __table_args__ = (
        UniqueConstraint('user_id', 'room_id', name='unique_user_room'),
    )
