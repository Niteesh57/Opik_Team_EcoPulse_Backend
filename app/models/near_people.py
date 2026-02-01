"""
NearPeople database model - tracks users' connections within their community
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class NearPeople(Base):
    __tablename__ = "near_people"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    near_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_id = Column(String, ForeignKey("rooms.room_id"), nullable=False)
    nickname = Column(String(100), nullable=True)  # Optional nickname for the neighbor
    notes = Column(Text, nullable=True)  # Optional notes about the neighbor
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="near_people_added")
    near_user = relationship("User", foreign_keys=[near_user_id], backref="added_as_near_person")
    room = relationship("Room", backref="near_people_connections")
    
    # Ensure a user can only add another user as near person once
    __table_args__ = (
        UniqueConstraint('user_id', 'near_user_id', name='unique_near_person'),
    )
