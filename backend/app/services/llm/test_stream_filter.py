import asyncio
import sys
import os

# Add parent dir to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.services.llm.stream_filter import StreamFilter

async def mock_stream():
    chunks = [
        "Task: Summarize the press release.\n",
        "Chunk 1: Data about statistics.\n",
        "Constraint 1: Be objective.\n",
        "\n",
        "### 社會保障摘要\n",
        "這份報告指出了...",
        "更多內容。"
    ]
    for c in chunks:
        yield c
        await asyncio.sleep(0.01)

async def test_filter():
    sf = StreamFilter()
    print("--- Starting Filter Test ---")
    async for filtered_chunk in sf.filter_stream(mock_stream()):
        print(f"[{filtered_chunk}]", end="", flush=True)
    print("\n--- End of Test ---")

if __name__ == "__main__":
    asyncio.run(test_filter())
