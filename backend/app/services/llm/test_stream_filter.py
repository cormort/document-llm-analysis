import asyncio
import os
import sys

# Add parent dir to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from app.services.llm.stream_filter import StreamFilter


async def run(chunks: list[str]) -> str:
    async def stream():
        for c in chunks:
            yield c

    return "".join([c async for c in StreamFilter().filter_stream(stream())])


def test_filter():
    out = asyncio.run(run([
        "Task: Summarize the press release.\n",
        "Chunk 1: Data about statistics.\n",
        "<think>hidden</think>",
        "### 社會保障摘要\n",
        "這份報告指出了...",
        "更多內容。",
    ]))
    assert out == "### 社會保障摘要\n這份報告指出了...更多內容。", out

    # A chunk that starts mid-line must not be mistaken for a thinking prefix.
    assert asyncio.run(run(["Tomorrow ", "I will go."])) == "Tomorrow I will go."

    # A trailing partial "<" is flushed at end of stream.
    assert asyncio.run(run(["a ", "<"])) == "a <"


if __name__ == "__main__":
    test_filter()
    print("ok")
