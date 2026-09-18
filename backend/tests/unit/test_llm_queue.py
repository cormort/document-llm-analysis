"""LLM Queue Service Tests."""

import asyncio
from datetime import datetime

import pytest

from app.services.llm_queue import LLMQueueService, QueueItem, QueueStatus


class TestQueueItem:
    def test_queue_item_creation(self):
        item = QueueItem(
            id="test-id",
            user_id=1,
            session_id="session-1",
            request_type="chat",
        )
        assert item.id == "test-id"
        assert item.user_id == 1
        assert item.status == QueueStatus.WAITING
        assert item.position == 0
        assert item.result is None
        assert item.error is None

    def test_queue_item_default_values(self):
        item = QueueItem(
            id="test-id", user_id=None, session_id=None, request_type="test"
        )
        assert item.created_at is not None
        assert isinstance(item.created_at, datetime)
        assert item.started_at is None
        assert item.completed_at is None


class TestLLMQueueService:
    def test_service_initialization(self):
        service = LLMQueueService(max_concurrent=2, timeout_seconds=60)
        assert service.max_concurrent == 2
        assert service.timeout_seconds == 60
        assert len(service.queue) == 0
        assert len(service.active_items) == 0

    @pytest.mark.asyncio
    async def test_enqueue_item(self):
        service = LLMQueueService()
        item = await service.enqueue("chat", user_id=1, session_id="s1")

        assert item.id is not None
        assert item.user_id == 1
        assert item.session_id == "s1"
        assert item.request_type == "chat"
        assert item.status == QueueStatus.WAITING
        assert item.position == 1

    @pytest.mark.asyncio
    async def test_enqueue_multiple_items(self):
        service = LLMQueueService()

        item1 = await service.enqueue("chat", user_id=1)
        item2 = await service.enqueue("chat", user_id=2)
        item3 = await service.enqueue("rag", user_id=3)

        assert item1.position == 1
        assert item2.position == 2
        assert item3.position == 3
        assert len(service.queue) == 3

    @pytest.mark.asyncio
    async def test_get_queue_status(self):
        service = LLMQueueService()
        await service.enqueue("chat", user_id=1)
        await service.enqueue("chat", user_id=2)

        status = service.get_status()

        assert status["queue_length"] == 2
        assert status["active_count"] == 0
        assert status["max_concurrent"] == 1

    @pytest.mark.asyncio
    async def test_get_user_position(self):
        service = LLMQueueService()

        await service.enqueue("chat", user_id=1)
        await service.enqueue("chat", user_id=2)

        pos1 = service.get_user_position(1)
        pos2 = service.get_user_position(2)

        assert pos1["position"] == 1
        assert pos2["position"] == 2

    @pytest.mark.asyncio
    async def test_get_user_position_nonexistent(self):
        service = LLMQueueService()
        pos = service.get_user_position(999)
        assert pos is None

    @pytest.mark.asyncio
    async def test_cancel_item(self):
        service = LLMQueueService()
        item = await service.enqueue("chat", user_id=1)

        result = await service.cancel(item.id)
        assert result is True
        assert item.status == QueueStatus.FAILED
        assert len(service.queue) == 0

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_item(self):
        service = LLMQueueService()
        result = await service.cancel("nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_status_with_items(self):
        service = LLMQueueService()
        await service.enqueue("chat", user_id=1)
        await service.enqueue("rag", user_id=2)

        status = service.get_status()

        assert len(status["waiting_items"]) == 2
        assert status["waiting_items"][0]["request_type"] == "chat"
        assert status["waiting_items"][1]["request_type"] == "rag"


class TestQueueDrain:
    """回歸測試：被喚醒的項目必須真正出隊，否則後續請求會永久逾時。"""

    @pytest.mark.asyncio
    async def test_third_request_is_not_starved(self, monkeypatch):
        import app.services.llm_queue as queue_module
        from app.services.llm_queue import acquire_llm, release_llm

        service = LLMQueueService(max_concurrent=1, timeout_seconds=2)
        monkeypatch.setattr(queue_module, "llm_queue", service)

        item1 = await acquire_llm("chat", user_id=1)
        assert item1.status == QueueStatus.PROCESSING
        assert service.get_status()["active_count"] == 1

        task2 = asyncio.create_task(acquire_llm("chat", user_id=2))
        task3 = asyncio.create_task(acquire_llm("chat", user_id=3))
        await asyncio.sleep(0.05)

        assert service.get_status()["queue_length"] == 2

        await release_llm(item1)
        item2 = await asyncio.wait_for(task2, timeout=1)
        assert item2.status == QueueStatus.PROCESSING
        # 出隊後不應再留在等待佇列中（原本的 bug）
        assert service.get_status()["queue_length"] == 1

        await release_llm(item2)
        item3 = await asyncio.wait_for(task3, timeout=1)
        assert item3.status == QueueStatus.PROCESSING
        assert service.get_status()["queue_length"] == 0

        await release_llm(item3)
        status = service.get_status()
        assert status["active_count"] == 0
        assert status["queue_length"] == 0

    @pytest.mark.asyncio
    async def test_wait_for_turn_timeout(self):
        service = LLMQueueService(max_concurrent=1, timeout_seconds=0)
        item = await service.enqueue("chat", user_id=1)
        got_turn = await service.wait_for_turn(item)
        assert got_turn is False
        assert item.status == QueueStatus.TIMEOUT
        assert len(service.queue) == 0
