"""
Room database model
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import uuid


def generate_room_id():
    """Generate a unique room ID"""
    return str(uuid.uuid4())[:8].upper()


class Room(Base):
    __tablename__ = "rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, unique=True, index=True, nullable=False, default=generate_room_id)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Room type flags
    doctor = Column(Boolean, default=False)
    shop = Column(Boolean, default=False)
    security = Column(Boolean, default=False)
    partyhall = Column(Boolean, default=False)
    cleaning = Column(Boolean, default=False)
    playground = Column(Boolean, default=False)
    
    # Staff assignments with availability
    # Format: {"doctor": {"user_id": 1, "available_timing": "9am-10pm", "days": "monday-friday"}}
    staff_assignments = Column(JSON, nullable=True, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    creator = relationship("User", backref="rooms")
