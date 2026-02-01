"""
CRUD operations for Notification model
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.notification import Notification
from app.schemas.notification import NotificationCreate, NotificationUpdate


def create_notification(db: Session, notification_in: NotificationCreate, from_user_id: int) -> Notification:
    db_notification = Notification(
        from_user_id=from_user_id,
        to_user_id=notification_in.to_user_id,
        message=notification_in.message,
        value=notification_in.value
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification

def create_notification_request(db: Session, notification_in: NotificationCreate, from_user_id: int) -> Notification:
    db_notification = Notification(
        to_user_id=notification_in.to_user_id,
        message=notification_in.message,
        value=notification_in.value
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification


def get_my_notifications(db: Session, user_id: int, skip: int = 0, limit: int = 50) -> List[Notification]:
    return (
        db.query(Notification)
        .filter(Notification.to_user_id == user_id)
        .order_by(desc(Notification.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_notification(db: Session, notification_id: int) -> Optional[Notification]:
    return db.query(Notification).filter(Notification.id == notification_id).first()


def update_notification(db: Session, notification: Notification, notification_in: NotificationUpdate) -> Notification:
    update_data = notification_in.model_dump(exclude_unset=True) if hasattr(notification_in, 'model_dump') else notification_in.dict(exclude_unset=True)
    
    # Auto-mark as read
    update_data["is_read"] = True
    
    for field, value in update_data.items():
        setattr(notification, field, value)
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_as_read(db: Session, user_id: int) -> bool:
    """Mark all notifications for a user as read"""
    db.query(Notification).filter(
        Notification.to_user_id == user_id,
        Notification.is_read == False
    ).update({Notification.is_read: True}, synchronize_session=False)
    db.commit()
    return True


def has_unread_notifications(db: Session, user_id: int) -> bool:
    """Check if user has any unread notifications"""
    return db.query(Notification).filter(
        Notification.to_user_id == user_id,
        Notification.is_read == False
    ).first() is not None


def expire_other_help_requests(
    db: Session, 
    from_user_id: int, 
    original_message: str, 
    exclude_user_id: int
):
    """
    When a help request (value=1) is accepted, mark all other identical requests 
    to other neighbors as expired (value=2).
    """
    db.query(Notification).filter(
        Notification.from_user_id == from_user_id,
        Notification.message == original_message,
        Notification.to_user_id != exclude_user_id,
        Notification.value == 1  # Only expire active help requests
    ).update({Notification.value: 2}, synchronize_session=False)
    db.commit()
