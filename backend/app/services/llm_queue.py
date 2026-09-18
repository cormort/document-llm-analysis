"""LLM 排隊系統服務。

管理 GPU 資源有限的情況下的 LLM 調用排隊。
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class QueueStatus(str, Enum):
    WAITING = "waiting"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class QueueItem:
    """佇列項目。"""

    id: str
    user_id: int | None
    session_id: str | None
    request_type: str
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: QueueStatus = QueueStatus.WAITING
    position: int = 0
    result: dict[str, Any] | None = None
    error: str | None = None
    event: asyncio.Event = field(default_factory=asyncio.Event)


class LLMQueueService:
    """LLM 排隊服務。"""

    def __init__(self, max_concurrent: int = 1, timeout_seconds: int = 300):
        self.max_concurrent = max_concurrent
        self.timeout_seconds = timeout_seconds
        self.queue: list[QueueItem] = []
        self.active_items: list[QueueItem] = []
        self.completed_items: list[QueueItem] = []
        self._lock = asyncio.Lock()
        self._process_task: asyncio.Task[None] | None = None

    async def enqueue(
        self,
        request_type: str,
        user_id: int | None = None,
        session_id: str | None = None,
    ) -> QueueItem:
        """加入佇列。"""
        item = QueueItem(
            id=str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            request_type=request_type,
        )
        await self.enqueue_item(item)
        return item

    async def enqueue_item(self, item: QueueItem) -> QueueItem:
        """把既有的 QueueItem 加入佇列（供 acquire_llm 直接取用）。"""
        async with self._lock:
            item.position = len(self.queue) + 1
            self.queue.append(item)
        return item

    async def try_acquire_immediately(self, item: QueueItem) -> bool:
        """沒有等待者且未達併發上限時，直接開始處理（在鎖內檢查，避免競態）。"""
        async with self._lock:
            if self.queue or len(self.active_items) >= self.max_concurrent:
                return False
            item.status = QueueStatus.PROCESSING
            item.started_at = datetime.now()
            self.active_items.append(item)
            return True

    async def wait_for_turn(self, item: QueueItem) -> bool:
        """等待輪到自己。"""
        try:
            await asyncio.wait_for(item.event.wait(), timeout=self.timeout_seconds)
            return True
        except TimeoutError:
            async with self._lock:
                if item in self.queue:
                    self.queue.remove(item)
                item.status = QueueStatus.TIMEOUT
            return False

    async def start_processing(self, item: QueueItem) -> None:
        """開始處理（從等待佇列移入 active_items）。"""
        async with self._lock:
            if item in self.queue:
                self.queue.remove(item)
            item.status = QueueStatus.PROCESSING
            item.started_at = datetime.now()
            if item not in self.active_items:
                self.active_items.append(item)
            self._update_positions()

    async def complete(
        self, item: QueueItem, result: dict[str, Any] | None = None
    ) -> None:
        """完成處理。"""
        async with self._lock:
            if item in self.active_items:
                self.active_items.remove(item)
            item.status = QueueStatus.COMPLETED
            item.completed_at = datetime.now()
            item.result = result
            self.completed_items.append(item)
            self._update_positions()
            self._notify_next()

    async def fail(self, item: QueueItem, error: str) -> None:
        """處理失敗。"""
        async with self._lock:
            if item in self.active_items:
                self.active_items.remove(item)
            if item in self.queue:
                self.queue.remove(item)
            item.status = QueueStatus.FAILED
            item.error = error
            self._update_positions()
            self._notify_next()

    def _update_positions(self) -> None:
        """更新佇列位置。"""
        for i, item in enumerate(self.queue):
            item.position = i + 1

    def _notify_next(self) -> None:
        """通知下一個等待者（填滿可用的併發名額）。"""
        available = self.max_concurrent - len(self.active_items)
        for item in self.queue[: max(0, available)]:
            item.event.set()

    def get_status(self) -> dict[str, Any]:
        """取得佇列狀態。"""
        return {
            "queue_length": len(self.queue),
            "active_count": len(self.active_items),
            "max_concurrent": self.max_concurrent,
            "waiting_items": [
                {
                    "id": item.id,
                    "position": item.position,
                    "user_id": item.user_id,
                    "request_type": item.request_type,
                    "created_at": item.created_at.isoformat(),
                    "wait_time_seconds": (
                        datetime.now() - item.created_at
                    ).total_seconds(),
                }
                for item in self.queue
            ],
            "active_items": [
                {
                    "id": item.id,
                    "user_id": item.user_id,
                    "request_type": item.request_type,
                    "started_at": item.started_at.isoformat()
                    if item.started_at
                    else None,
                }
                for item in self.active_items
            ],
        }

    def get_user_position(self, user_id: int) -> dict[str, Any] | None:
        """取得用戶在佇列中的位置。"""
        for item in self.queue:
            if item.user_id == user_id:
                return {
                    "id": item.id,
                    "position": item.position,
                    "status": item.status.value,
                    "wait_time_seconds": (
                        datetime.now() - item.created_at
                    ).total_seconds(),
                }
        return None

    async def cancel(self, item_id: str) -> bool:
        """取消佇列項目。"""
        async with self._lock:
            for item in self.queue:
                if item.id == item_id:
                    self.queue.remove(item)
                    item.status = QueueStatus.FAILED
                    item.error = "使用者取消"
                    self._update_positions()
                    return True
        return False


llm_queue = LLMQueueService(max_concurrent=1, timeout_seconds=300)


async def acquire_llm(
    request_type: str,
    user_id: int | None = None,
    session_id: str | None = None,
) -> QueueItem:
    """取得 LLM 使用權。

    修正重點：先前從等待佇列被喚醒後，**沒有任何人呼叫 start_processing**，
    項目會永遠留在 `queue` 裡；`complete()` 的 `_notify_next()` 因此永遠只會
    叫醒同一個殘留項目，第三個之後的請求會一路等到 timeout。
    """
    item = QueueItem(
        id=str(uuid.uuid4()),
        user_id=user_id,
        session_id=session_id,
        request_type=request_type,
    )

    if await llm_queue.try_acquire_immediately(item):
        return item

    await llm_queue.enqueue_item(item)

    got_turn = await llm_queue.wait_for_turn(item)

    if not got_turn:
        raise TimeoutError("等待 LLM 超時")

    # 被喚醒後必須真正出隊並佔用一個併發名額
    await llm_queue.start_processing(item)
    return item


async def release_llm(item: QueueItem, result: dict | None = None) -> None:
    """釋放 LLM 使用權。"""
    await llm_queue.complete(item, result)
