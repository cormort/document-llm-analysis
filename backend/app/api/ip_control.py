"""IP 存取控制 API 端點。"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import get_current_admin_user
from app.core.database import get_db
from app.models.ip_control import IPWhitelist, IPBlacklist, IPAccessLog
from app.models.user import User

router = APIRouter()


class IPEntryCreate(BaseModel):
    ip_address: str
    description: str | None = None
    reason: str | None = None
    expires_days: int | None = None


class IPEntryResponse(BaseModel):
    id: int
    ip_address: str
    description: str | None
    created_at: datetime
    created_by: int | None
    is_active: bool

    class Config:
        from_attributes = True


class IPBlacklistResponse(BaseModel):
    id: int
    ip_address: str
    reason: str | None
    created_at: datetime
    expires_at: datetime | None
    is_active: bool

    class Config:
        from_attributes = True


class IPAccessLogResponse(BaseModel):
    id: int
    ip_address: str
    user_id: int | None
    action: str
    path: str | None
    is_blocked: bool
    block_reason: str | None
    created_at: datetime

    class Config:
        from_attributes = True


def check_ip_access(ip_address: str, db: Session) -> tuple[bool, str | None]:
    """檢查 IP 是否有存取權限。"""
    now = datetime.now(timezone.utc)

    blacklist_entry = db.execute(
        select(IPBlacklist)
        .where(
            IPBlacklist.ip_address == ip_address,
            IPBlacklist.is_active == True,
        )
        .where((IPBlacklist.expires_at.is_(None)) | (IPBlacklist.expires_at > now))
    ).scalar_one_or_none()

    if blacklist_entry:
        return False, f"IP 在黑名單中: {blacklist_entry.reason}"

    whitelist_count = (
        db.execute(select(IPWhitelist).where(IPWhitelist.is_active == True))
        .scalars()
        .all()
    )

    if len(whitelist_count) > 0:
        in_whitelist = db.execute(
            select(IPWhitelist).where(
                IPWhitelist.ip_address == ip_address,
                IPWhitelist.is_active == True,
            )
        ).scalar_one_or_none()

        if not in_whitelist:
            return False, "IP 不在白名單中"

    return True, None


def log_ip_access(
    db: Session,
    ip_address: str,
    action: str,
    path: str | None,
    user_id: int | None = None,
    user_agent: str | None = None,
    is_blocked: bool = False,
    block_reason: str | None = None,
) -> None:
    """記錄 IP 存取。"""
    log = IPAccessLog(
        ip_address=ip_address,
        user_id=user_id,
        action=action,
        path=path,
        user_agent=user_agent,
        is_blocked=is_blocked,
        block_reason=block_reason,
    )
    db.add(log)
    db.commit()


@router.get("/whitelist", response_model=list[IPEntryResponse])
def list_whitelist(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
    skip: int = 0,
    limit: int = 100,
) -> list[IPWhitelist]:
    """取得 IP 白名單列表。"""
    entries = (
        db.execute(
            select(IPWhitelist)
            .order_by(IPWhitelist.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return list(entries)


@router.post(
    "/whitelist", response_model=IPEntryResponse, status_code=status.HTTP_201_CREATED
)
def add_to_whitelist(
    data: IPEntryCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
) -> IPWhitelist:
    """新增 IP 到白名單。"""
    existing = db.execute(
        select(IPWhitelist).where(IPWhitelist.ip_address == data.ip_address)
    ).scalar_one_or_none()

    if existing:
        if existing.is_active:
            raise HTTPException(status_code=400, detail="IP 已在白名單中")
        existing.is_active = True
        existing.description = data.description
        db.commit()
        db.refresh(existing)
        return existing

    entry = IPWhitelist(
        ip_address=data.ip_address,
        description=data.description,
        created_by=current_user.id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/whitelist/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_whitelist(
    entry_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
) -> None:
    """從白名單移除 IP。"""
    entry = db.execute(
        select(IPWhitelist).where(IPWhitelist.id == entry_id)
    ).scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="找不到此白名單項目")

    entry.is_active = False
    db.commit()


@router.get("/blacklist", response_model=list[IPBlacklistResponse])
def list_blacklist(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
) -> list[IPBlacklist]:
    """取得 IP 黑名單列表。"""
    query = select(IPBlacklist)
    if active_only:
        query = query.where(IPBlacklist.is_active == True)

    entries = (
        db.execute(
            query.order_by(IPBlacklist.created_at.desc()).offset(skip).limit(limit)
        )
        .scalars()
        .all()
    )
    return list(entries)


@router.post(
    "/blacklist",
    response_model=IPBlacklistResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_to_blacklist(
    data: IPEntryCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
) -> IPBlacklist:
    """新增 IP 到黑名單。"""
    existing = db.execute(
        select(IPBlacklist).where(IPBlacklist.ip_address == data.ip_address)
    ).scalar_one_or_none()

    if existing:
        if existing.is_active:
            raise HTTPException(status_code=400, detail="IP 已在黑名單中")
        existing.is_active = True
        existing.reason = data.reason
        db.commit()
        db.refresh(existing)
        return existing

    expires_at = None
    if data.expires_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_days)

    entry = IPBlacklist(
        ip_address=data.ip_address,
        reason=data.reason,
        created_by=current_user.id,
        expires_at=expires_at,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/blacklist/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_blacklist(
    entry_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
) -> None:
    """從黑名單移除 IP。"""
    entry = db.execute(
        select(IPBlacklist).where(IPBlacklist.id == entry_id)
    ).scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="找不到此黑名單項目")

    entry.is_active = False
    db.commit()


@router.get("/logs", response_model=list[IPAccessLogResponse])
def list_access_logs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
    ip_address: str | None = None,
    days: int = 7,
    skip: int = 0,
    limit: int = 100,
) -> list[IPAccessLog]:
    """取得 IP 存取記錄。"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    query = select(IPAccessLog).filter(IPAccessLog.created_at >= start_date)

    if ip_address:
        query = query.filter(IPAccessLog.ip_address == ip_address)

    logs = (
        db.execute(
            query.order_by(IPAccessLog.created_at.desc()).offset(skip).limit(limit)
        )
        .scalars()
        .all()
    )
    return list(logs)


@router.get("/stats")
def get_ip_stats(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
    days: int = 7,
) -> dict:
    """取得 IP 統計資訊。"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    whitelist_count = (
        db.execute(select(IPWhitelist).where(IPWhitelist.is_active == True))
        .scalars()
        .all()
    )

    blacklist_count = (
        db.execute(select(IPBlacklist).where(IPBlacklist.is_active == True))
        .scalars()
        .all()
    )

    blocked_logs = (
        db.execute(
            select(IPAccessLog).where(
                IPAccessLog.is_blocked == True,
                IPAccessLog.created_at >= start_date,
            )
        )
        .scalars()
        .all()
    )

    unique_ips = (
        db.execute(
            select(IPAccessLog.ip_address)
            .where(
                IPAccessLog.created_at >= start_date,
            )
            .distinct()
        )
        .scalars()
        .all()
    )

    return {
        "whitelist_count": len(whitelist_count),
        "blacklist_count": len(blacklist_count),
        "blocked_attempts": len(blocked_logs),
        "unique_ips": len(unique_ips),
    }
