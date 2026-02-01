"""
API endpoints for Notifications
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.crud import notification as notification_crud
from app.schemas.notification import NotificationCreate, NotificationOut, NotificationUpdate
from app.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("/", response_model=NotificationOut)
async def create_notification(
    notification_in: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new notification.
    """
    # Ensure current user cannot set arbitrary from_user_id, it is always themselves
    notification = notification_crud.create_notification(
        db, notification_in=notification_in, from_user_id=current_user.id
    )
    
    noti_out = NotificationOut.from_orm(notification)
    noti_out.from_username = current_user.username
    return noti_out


@router.post("/read-all", response_model=dict)
async def read_all_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Mark all notifications as read for the current user.
    """
    notification_crud.mark_all_as_read(db, user_id=current_user.id)
    return {"status": "success", "message": "All notifications marked as read"}


@router.get("/", response_model=dict)
async def list_my_notifications(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List notifications for the current user.
    Returns:
        results: List of notifications
        messages: Boolean (True if all messages are read, False if any unread)
    """
    notifications = notification_crud.get_my_notifications(db, user_id=current_user.id, skip=skip, limit=limit)
    
    # Check if there are ANY unread notifications
    has_unread = notification_crud.has_unread_notifications(db, user_id=current_user.id)
    
    # Logic: if all messages are read (has_unread is False) -> messages = True
    # If there are unread messages (has_unread is True) -> messages = False
    messages_status = not has_unread
    
    results = []
    for noti in notifications:
        noti_out = NotificationOut.from_orm(noti)
        if noti.from_user:
            noti_out.from_username = noti.from_user.username
        results.append(noti_out)
        
    return {
        "results": results,
        "messages": messages_status
    }


@router.put("/{notification_id}", response_model=NotificationOut)
async def update_notification(
    notification_id: int,
    notification_in: NotificationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update a notification (e.g. mark as read).
    User can only update their own received notifications.
    
    Special Logic for Help Requests (value=1):
    - If user marks it as read (is_read=True), it's treated as "Accepted".
    - Notify the sender that this user accepted.
    - Expire all other identical notifications (value=2).
    """
    notification = notification_crud.get_notification(db, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    if notification.to_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this notification")
        
    # Check for Help Request Acceptance Logic
    # Condition: It's a help request (value=1) AND user is marking it as read
    is_help_request = notification.value == 1
    marking_as_read = notification_in.is_read is True
    
    updated_notification = notification_crud.update_notification(db, notification, notification_in)
    
    if updated_notification.value == 1 and updated_notification.to_user_id is not None and updated_notification.from_user_id is not None:
        # 1. Notify the original sender (if they exist)
        if updated_notification.from_user_id:
            accept_msg = NotificationCreate(
                to_user_id=updated_notification.from_user_id,
                message=f"{current_user.username} accepted your help request! Please coordinate with them.",
                value=0 # Normal notification
            )
            # When accepting, the 'from' is the neighbor (current_user)
            notification_crud.create_notification_request(db, notification_in=accept_msg, from_user_id=current_user.id)
            
            # 2. Expire other neighbors' requests (set value=2)
            notification_crud.expire_other_help_requests(
                db, 
                from_user_id=updated_notification.from_user_id,
                original_message=updated_notification.message,
                exclude_user_id=current_user.id
            )
    
    noti_out = NotificationOut.from_orm(updated_notification)
    noti_out.from_username = updated_notification.from_user.username
    return noti_out
