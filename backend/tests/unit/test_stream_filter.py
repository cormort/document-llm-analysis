"""StreamFilter 的回歸測試。

原始 bug：`<thinking>...</thinking>` 被誤判為 tag `think`，因為找不到
`</think>` 而把整段回答（含真正的答案）全部丟棄。
"""

from collections.abc import AsyncGenerator

import pytest

from app.services.llm.stream_filter import StreamFilter


async def _stream(chunks: list[str]) -> AsyncGenerator[str, None]:
    for chunk in chunks:
        yield chunk


async def _run(chunks: list[str]) -> str:
    filter_ = StreamFilter()
    out: list[str] = []
    async for piece in filter_.filter_stream(_stream(chunks)):
        out.append(piece)
    return "".join(out)


@pytest.mark.asyncio
async def test_thinking_tag_does_not_swallow_answer():
    text = "<thinking>internal reasoning here</thinking>最終答案"
    assert await _run([text]) == "最終答案"


@pytest.mark.asyncio
async def test_think_tag():
    assert await _run(["<think>hmm</think>answer"]) == "answer"


@pytest.mark.asyncio
async def test_thinking_tag_split_across_chunks():
    chunks = ["<thin", "king>secret</thin", "king>答案內容"]
    assert await _run(chunks) == "答案內容"


@pytest.mark.asyncio
async def test_think_then_thinking_in_same_stream():
    text = "<think>a</think>中間<thinking>b</thinking>結尾"
    assert await _run([text]) == "中間結尾"


@pytest.mark.asyncio
async def test_close_tag_with_space():
    assert await _run(["<thinking>x</thinking >答案"]) == "答案"


@pytest.mark.asyncio
async def test_plain_text_passes_through():
    assert await _run(["這是普通的回答"]) == "這是普通的回答"


@pytest.mark.asyncio
async def test_similar_tag_is_not_treated_as_thought():
    """<thinktank> 不該被當成思考標籤。"""
    expected = "<thinktank>保留我</thinktank>"
    assert await _run([expected]) == expected


@pytest.mark.asyncio
async def test_prefix_lines_are_filtered():
    out = await _run(["Task: 不該出現\n這是答案"])
    assert "Task:" not in out
    assert "這是答案" in out


@pytest.mark.asyncio
async def test_unclosed_thought_block_is_dropped():
    assert await _run(["<thinking>沒有收尾"]) == ""
