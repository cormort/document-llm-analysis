import re


# XML-style thought tags used by various LLMs (Gemma, DeepSeek, QwQ, etc.)
_THOUGHT_TAGS = ["think", "thought", "thinking", "reasoning", "internal", "scratchpad"]
_THOUGHT_TAG_PATTERN = re.compile(
    r"<(?:" + "|".join(_THOUGHT_TAGS) + r")[\s\S]*?</(?:" + "|".join(_THOUGHT_TAGS) + r")>",
    re.IGNORECASE,
)


def clean_rag_content(content: str) -> str:
    """
    清理 RAG 內容中的特殊字符、thinking blocks 與控制字元。

    適用於：LLM 生成的回答、從文件檢索的 context。
    """
    if not content:
        return ""

    if not isinstance(content, str):
        content = str(content)

    # Remove null bytes
    content = content.replace("\x00", "")

    # Remove XML-style thought/thinking tags (e.g., <think>...</think>)
    content = _THOUGHT_TAG_PATTERN.sub("", content)

    # Remove list containing a thinking dict (single or double quotes)
    content = re.sub(
        r"\[\s*\{[^\}]*(['\"]type['\"]\s*:\s*['\"]thinking['\"])\b[^\}]*\}\s*\]",
        "",
        content,
        flags=re.DOTALL,
    )
    # Remove dict containing a thinking key (single or double quotes)
    content = re.sub(
        r"\{[^\}]*(['\"]type['\"]\s*:\s*['\"]thinking['\"])\b[^\}]*\}",
        "",
        content,
        flags=re.DOTALL,
    )

    content = re.sub(
        r"\[\{'type': 'thinking', 'thinking': .*?\}\]", "", content, flags=re.DOTALL
    )

    # Remove any Paste marker, even if truncated (e.g., "[Pasted ~1 lin]")
    content = re.sub(r"\[Pasted ~\d+ lin[^\]]*\]", "", content)
    content = re.sub(r"\[Pasted ~\d+ lines?\]", "", content)

    # Remove control characters (except newlines and tabs)
    content = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", content)

    # Collapse excessive newlines
    content = re.sub(r"\n{3,}", "\n\n", content)

    return content.strip()


def clean_text_for_display(text: str) -> str:
    """
    清理文本中的特殊字符，確保在前端正確顯示。

    適用於：一般文字顯示（非 LLM 輸出），只清除控制字元。
    """
    if not text:
        return ""

    if not isinstance(text, str):
        text = str(text)

    text = text.replace("\x00", "")
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

    return text
