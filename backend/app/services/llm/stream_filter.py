import re
from typing import AsyncGenerator


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

    # Gemma 4 / DeepSeek / QwQ use <think>, others use <thinking> etc.
    THOUGHT_TAGS = ["think", "thought", "thinking", "reasoning", "internal", "scratchpad"]

    def __init__(self):
        self.buffer = ""
        self.in_thought_block = False
        self.current_tag = None

    def _find_thought_tag_open(self, text: str) -> tuple[int, str] | None:
        for tag in self.THOUGHT_TAGS:
            pattern = f"<{tag}"
            idx = text.lower().find(pattern)
            if idx != -1:
                return idx, tag
        return None

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
        close_tag = f"</{tag}>"
        if f"</{tag}" in text_lower:
            return True
        if any(text_lower.endswith(f"</{tag[:i]}") for i in range(1, len(tag) + 1)):
            return True
        if text_lower.endswith("</") or text_lower.endswith("<"):
            return True
        return False

    def _find_tag_close(self, text: str, tag: str) -> int:
        close_pattern = f"</{tag}>"
        return text.lower().find(close_pattern)

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
                        idx, tag = found
                        before_tag = self.buffer[:idx]
                        after_open_tag = self.buffer[idx:]
                        close_idx = self._find_tag_close(after_open_tag, tag)

                        if close_idx != -1:
                            close_tag_len = len(f"</{tag}>")
                            after_content = after_open_tag[close_idx + close_tag_len :]
                            self.buffer = before_tag + after_content
                            processed = True
                            continue
                        else:
                            if before_tag:
                                yield self._filter_prefixes(before_tag)
                            self.in_thought_block = True
                            self.current_tag = tag
                            self.buffer = ""
                            break
                    elif self._find_potential_tag_open(self.buffer):
                        break

                if self.in_thought_block:
                    close_idx = self._find_tag_close(self.buffer, self.current_tag)
                    if close_idx != -1:
                        close_tag_len = len(f"</{self.current_tag}>")
                        self.buffer = self.buffer[close_idx + close_tag_len :]
                        self.in_thought_block = False
                        self.current_tag = None
                        processed = True
                        continue
                    elif self._find_potential_tag_close(self.buffer, self.current_tag):
                        break
                    else:
                        self.buffer = ""
                        break

                if not processed:
                    break

            if self.in_thought_block:
                continue

            if self.buffer.strip() and not self._find_potential_tag_open(self.buffer):
                yield self._filter_prefixes(self.buffer)
                self.buffer = ""
