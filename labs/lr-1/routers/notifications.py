from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from connection import get_session
from models import Notifications, Users
from schemas import NotificationRead
from routers.auth import get_current_user
from typing import List

router = APIRouter(prefix = "/notifications", tags = ["Notifications"])


@router.get("/", response_model = List[NotificationRead])
def read_notifications(
    unread_only: bool = False,
    current_user: Users = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    statement = select(Notifications).where(Notifications.user_id == current_user.user_id)
    if unread_only:
        statement = statement.where(Notifications.is_read == False)
    notifications = session.exec(statement).all()
    return notifications


@router.get("/{notification_id}", response_model = NotificationRead)
def read_notification(
    notification_id: int,
    current_user: Users = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    notification = session.get(Notifications, notification_id)
    if not notification:
        raise HTTPException(status_code = 404, detail = "Notification not found")
    if notification.user_id != current_user.user_id:
        raise HTTPException(status_code = 403, detail = "Not authorized to view this notification")
    return notification


@router.patch("/{notification_id}/mark-read", response_model = NotificationRead)
def mark_notification_read(
    notification_id: int,
    current_user: Users = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    notification = session.get(Notifications, notification_id)
    if not notification:
        raise HTTPException(status_code = 404, detail = "Notification not found")
    if notification.user_id != current_user.user_id:
        raise HTTPException(status_code = 403, detail = "Not authorized to update this notification")
    notification.is_read = True
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return notification
