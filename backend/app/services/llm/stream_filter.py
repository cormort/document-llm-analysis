"""過濾 LLM 輸出中的「思考過程」與自言自語。

修正重點（原本的 bug）：
`THOUGHT_TAGS` 以 `"think"` 開頭，而 `_find_thought_tag_open` 用
`text.find("<think")` 依序比對並直接回傳第一個命中的 tag，
因此 `<thinking>...</thinking>` 會被誤判成 tag `think`，
接著去尋找永遠不存在的 `</think>`，導致**整段回答被吃掉**。

現在改成：
1. 取「最早出現」的 tag；同一位置若多個 tag 都匹配，取**最長**的那個
   （`thinking` 優先於 `think`）。
2. tag 後面必須接 `>` 或空白，避免 `<thinktank>` 之類的誤判。
3. 收尾標籤允許 `</tag>` 與 `</tag >`。
"""

import re
from collections.abc import AsyncGenerator


class StreamFilter:
    """
    Filters LLM output streams to remove common 'thinking' or 'monologue' patterns.
    Handles:
    - Patterns like 'Task: ...', 'Chunk X: ...'
    - XML-like tags like <thought>...</thought>, <thinking>...</thinking>
    """

    THINKING_PREFIXES = [
        r"^Task:",
        r"^Chunk \d+:",
        r"^Constraint \d+:",
        r"^Context:",
        r"^\*Draft:",
        r"^\*Subject:",
        r"^Step \d+:",
        r"^Analysis:",
        r"^Reasoning:",
        r"^Self-Correction",
        r"^\(Self-correction",
        r"^Double-check",
        r"^Final Polish",
        r"^Refining Data",
        r"^Check against rules",
        r"^Wait,",
        r"^Draft:",
        r"^Note:",
        r"^Let me",
        r"^I need to",
        r"^I will",
        r"^I should",
        r"^I'll",
    ]

    # Gemma / DeepSeek / QwQ use <think>, others use <thinking> etc.
    # 注意順序不影響判定（會取最長匹配），但由長到短可讀性較好。
    THOUGHT_TAGS = [
        "thinking",
        "thought",
        "reasoning",
        "scratchpad",
        "internal",
        "think",
    ]

    def __init__(self):
        self.buffer = ""
        self.in_thought_block = False
        self.current_tag = None

    # ------------------------------------------------------------------
    # Tag helpers
    # ------------------------------------------------------------------
    def _find_thought_tag_open(self, text: str) -> tuple[int, str, int] | None:
        """回傳 (tag 起始索引, tag 名稱, 內容起始索引)；取最早出現、同位置取最長者。

        只有當 `<tag ...>` 的 `>` 已經出現在 buffer 中時才算命中；
        標籤還沒收尾（例如 chunk 結尾剛好切成 `"<thin"`）時回傳 None，
        由 `_find_potential_tag_open` 讓呼叫端繼續等待後續 chunk。
        """
        lower = text.lower()
        best: tuple[int, str, int] | None = None
        for tag in self.THOUGHT_TAGS:
            idx = 0
            while True:
                idx = lower.find(f"<{tag}", idx)
                if idx == -1:
                    break
                end = idx + len(tag) + 1
                following = lower[end : end + 1]
                # 標籤後面必須是 `>` 或空白（允許 <think >），否則可能是 <thinktank>
                if following in (">", " ", "\t", "\n", "\r"):
                    gt = lower.find(">", end)
                    if gt == -1:
                        return best  # 標籤尚未收尾，等更多資料
                    if (
                        best is None
                        or idx < best[0]
                        or (idx == best[0] and len(tag) > len(best[1]))
                    ):
                        best = (idx, tag, gt + 1)
                    break
                idx += 1
        return best

    def _find_potential_tag_open(self, text: str) -> bool:
        """Check if buffer might be starting a thought tag (partial match)."""
        text_lower = text.lower()
        for tag in self.THOUGHT_TAGS:
            if text_lower.endswith("<") or any(
                text_lower.endswith(f"<{tag[:i]}") for i in range(1, len(tag) + 1)
            ):
                return True
        return False

    def _find_potential_tag_close(self, text: str, tag: str) -> bool:
        """Check if buffer might be starting a close tag (partial match)."""
        text_lower = text.lower()
        if f"</{tag}" in text_lower:
            return True
        if any(text_lower.endswith(f"</{tag[:i]}") for i in range(1, len(tag) + 1)):
            return True
        return text_lower.endswith("</") or text_lower.endswith("<")

    def _find_tag_close(self, text: str, tag: str) -> tuple[int, int] | None:
        """找收尾標籤。

        Returns:
            (起始索引, 結束索引（不含）) 或 None。支援 `</tag>` 與 `</tag >`。
        """
        match = re.search(rf"</{re.escape(tag)}\s*>", text, re.IGNORECASE)
        if not match:
            return None
        return match.start(), match.end()

    def _filter_prefixes(self, text: str) -> str:
        """Filter out lines that start with thinking prefixes."""
        lines = text.split("\n")
        filtered_lines = []
        for line in lines:
            stripped = line.strip()
            is_prefix = any(
                re.match(p, stripped, re.IGNORECASE) for p in self.THINKING_PREFIXES
            )
            if not is_prefix:
                filtered_lines.append(line)
        return "\n".join(filtered_lines)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    async def filter_stream(
        self, stream: AsyncGenerator[str, None]
    ) -> AsyncGenerator[str, None]:
        """Processes an async stream of text chunks and yields filtered chunks."""
        async for chunk in stream:
            self.buffer += chunk

            while True:
                processed = False

                if not self.in_thought_block:
                    found = self._find_thought_tag_open(self.buffer)
                    if found:
                        idx, tag, content_start = found
                        before_tag = self.buffer[:idx]
                        after_open_tag = self.buffer[idx:]
                        close = self._find_tag_close(after_open_tag, tag)

                        if close is not None:
                            _, close_end = close
                            after_content = after_open_tag[close_end:]
                            self.buffer = before_tag + after_content
                            processed = True
                            continue
                        if before_tag:
                            yield self._filter_prefixes(before_tag)
                        self.in_thought_block = True
                        self.current_tag = tag
                        # 保留開標籤之後的內容：裡面可能已經有（部分的）收尾標籤
                        self.buffer = after_open_tag[content_start:]
                        break
                    if self._find_potential_tag_open(self.buffer):
                        break

                if self.in_thought_block:
                    close = self._find_tag_close(self.buffer, self.current_tag)
                    if close is not None:
                        _, close_end = close
                        self.buffer = self.buffer[close_end:]
                        self.in_thought_block = False
                        self.current_tag = None
                        processed = True
                        continue
                    if self._find_potential_tag_close(self.buffer, self.current_tag):
                        break
                    self.buffer = ""
                    break

                if not processed:
                    break

            if self.in_thought_block:
                continue

            if self.buffer.strip() and not self._find_potential_tag_open(self.buffer):
                yield self._filter_prefixes(self.buffer)
                self.buffer = ""
