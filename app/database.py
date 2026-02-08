"""
Database configuration and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from typing import Generator
from app.core.config import settings

# Determine DB URL - Prioritize SQLite if requested or default
db_url = settings.DATABASE_URL
# Force SQLite if the configuration still points to the remote Postgres DB
# to satisfy the "use sqlite" requirement despite .env overrides
if "neondb" in db_url or "postgresql" in db_url:
    db_url = "sqlite:///./sql_app.db"

if db_url.startswith("sqlite"):
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool, # Use StaticPool for in-memory/file SQLite to avoid threading issues
        pool_pre_ping=True
    )
else:
    # 1. Enhanced Engine Configuration
    # pool_size=10: Keeps 10 connections ready to go.
    # max_overflow=5: Allows 5 extra if traffic spikes (total 15).
    # pool_recycle: Prevents "idle connection" errors by refreshing connections every 30 mins.
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=10,
        max_overflow=5,
        # pool_pre_ping=True,  # Checks if connection is alive before using it
        pool_recycle=1800,   # Matches most cloud provider idle timeouts
        pool_reset_on_return='rollback',  # Resets session state on return
        connect_args={"options": "-c timezone=utc"} # Ensures consistent time handling
    )

# 2. Session Factory
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)

# 3. Modern Base Class (SQLAlchemy 2.0 style)
Base = declarative_base()

def get_db() -> Generator:
    """
    Dependency to get database session. 
    Ensures the session is closed even if an exception occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initialize database tables.
    Note: In production, consider using Alembic for migrations 
    instead of Base.metadata.create_all.
    """
    # Import models here to ensure they are registered
    from app.models.user import User
    from app.models.room import Room
    from app.models.user_room import UserRoom
    from app.models.message import MessageSession, UserMessage
    from app.models.event import Event
    from app.models.event_user import EventUser
    from app.models.near_people import NearPeople
    
    Base.metadata.create_all(bind=engine)