"""行為追蹤 API 端點。"""

import json
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.auth import get_current_admin_user, get_current_user
from app.core.database import get_db
from app.models.analytics import AnalyticsEvent
from app.models.user import User

router = APIRouter()


class TrackEvent(BaseModel):
    event_type: str
    event_name: str
    event_data: dict[str, Any] | None = None
    page_url: str | None = None
    session_id: str | None = None


class EventStats(BaseModel):
    event_name: str
    total_count: int
    unique_users: int


@router.post("/track", status_code=201)
async def track_event(
    request: Request,
    event_data: TrackEvent,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    """記錄使用者行為事件。"""
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    user = None
    if token:
        try:
            from app.core.security import decode_access_token

            payload = decode_access_token(token)
            if payload and payload.get("user_id"):
                user = db.get(User, payload["user_id"])
        except Exception:
            pass

    event = AnalyticsEvent(
        user_id=user.id if user else None,
        event_type=event_data.event_type,
        event_name=event_data.event_name,
        event_data=json.dumps(event_data.event_data) if event_data.event_data else None,
        page_url=event_data.page_url,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
        session_id=event_data.session_id,
    )
    db.add(event)
    db.commit()

    return {"status": "ok", "event_id": str(event.id)}


@router.get("/stats", response_model=list[EventStats])
def get_event_stats(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
    days: int = 7,
) -> list[dict[str, Any]]:
    """取得事件統計（需管理員權限）。"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    results = (
        db.query(
            AnalyticsEvent.event_name,
            func.count(AnalyticsEvent.id).label("total_count"),
            func.count(func.distinct(AnalyticsEvent.user_id)).label("unique_users"),
        )
        .filter(AnalyticsEvent.created_at >= start_date)
        .group_by(AnalyticsEvent.event_name)
        .all()
    )

    return [
        {
            "event_name": r.event_name,
            "total_count": r.total_count,
            "unique_users": r.unique_users,
        }
        for r in results
    ]


@router.get("/events")
def list_events(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
    event_type: str | None = None,
    user_id: int | None = None,
    days: int = 7,
    skip: int = 0,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """取得事件列表（需管理員權限）。"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    query = select(AnalyticsEvent).filter(AnalyticsEvent.created_at >= start_date)

    if event_type:
        query = query.filter(AnalyticsEvent.event_type == event_type)
    if user_id:
        query = query.filter(AnalyticsEvent.user_id == user_id)

    query = query.order_by(AnalyticsEvent.created_at.desc()).offset(skip).limit(limit)

    events = db.execute(query).scalars().all()

    return [
        {
            "id": e.id,
            "user_id": e.user_id,
            "event_type": e.event_type,
            "event_name": e.event_name,
            "event_data": json.loads(e.event_data) if e.event_data else None,
            "page_url": e.page_url,
            "ip_address": e.ip_address,
            "session_id": e.session_id,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


@router.get("/my-events")
def get_my_events(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: int = 30,
    skip: int = 0,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """取得當前用戶的事件記錄。"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    events = (
        db.execute(
            select(AnalyticsEvent)
            .filter(AnalyticsEvent.user_id == current_user.id)
            .filter(AnalyticsEvent.created_at >= start_date)
            .order_by(AnalyticsEvent.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )

    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "event_name": e.event_name,
            "event_data": json.loads(e.event_data) if e.event_data else None,
            "page_url": e.page_url,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]
