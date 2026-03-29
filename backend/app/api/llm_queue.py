"""LLM 排隊狀態 API 端點。"""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.llm_queue import llm_queue

router = APIRouter()


class QueueStatusResponse(BaseModel):
    queue_length: int
    active_count: int
    max_concurrent: int
    your_position: int | None
    your_wait_time: float | None
    estimated_wait_seconds: float


class FullQueueStatus(BaseModel):
    queue_length: int
    active_count: int
    max_concurrent: int
    waiting_items: list[dict[str, Any]]
    active_items: list[dict[str, Any]]


@router.get("/status", response_model=QueueStatusResponse)
def get_queue_status(
    current_user: Annotated[User | None, Depends(get_current_user)] = None,
) -> dict:
    """取得佇列狀態。"""
    status = llm_queue.get_status()

    user_position = None
    user_wait_time = None

    if current_user:
        user_info = llm_queue.get_user_position(current_user.id)
        if user_info:
            user_position = user_info["position"]
            user_wait_time = user_info["wait_time_seconds"]

    avg_wait_time = 30

    estimated_wait = 0
    if user_position and user_position > 1:
        estimated_wait = (user_position - 1) * avg_wait_time

    return {
        "queue_length": status["queue_length"],
        "active_count": status["active_count"],
        "max_concurrent": status["max_concurrent"],
        "your_position": user_position,
        "your_wait_time": user_wait_time,
        "estimated_wait_seconds": estimated_wait,
    }


@router.get("/full-status", response_model=FullQueueStatus)
def get_full_status(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """取得完整佇列狀態（需登入）。"""
    return llm_queue.get_status()


@router.post("/cancel/{item_id}")
async def cancel_queue_item(
    item_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """取消佇列項目。"""
    success = await llm_queue.cancel(item_id)
    if success:
        return {"status": "cancelled", "item_id": item_id}
    return {"status": "not_found", "item_id": item_id}
