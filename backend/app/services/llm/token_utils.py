"""
Token Estimation Utilities
Provides heuristic-based token counting for CJK/Latin mixed text.
"""


def estimate_tokens_heuristic(text: str) -> int:
    """Estimate token count using character-based heuristics.

    For CJK text (Chinese/Japanese/Korean), each character is approximately
    0.6-1.0 tokens depending on the tokenizer. For ASCII/Latin text,
    it's roughly 0.25 tokens per character (≈4 chars per token).

    We use a conservative mixed estimate that scans the text for CJK density.

    Args:
        text: Input text to estimate tokens for.

    Returns:
        Estimated token count.
    """
    if not text:
        return 0

    cjk_ranges = [
        (0x4E00, 0x9FFF),
        (0x3400, 0x4DBF),
        (0x20000, 0x2A6DF),
        (0x2A700, 0x2B73F),
        (0x2B740, 0x2B81F),
        (0x2B820, 0x2CEAF),
        (0xF900, 0xFAFF),
        (0x2F800, 0x2FA1F),
    ]

    cjk_count = 0
    total_chars = len(text)

    for char in text:
        code_point = ord(char)
        for start, end in cjk_ranges:
            if start <= code_point <= end:
                cjk_count += 1
                break

    non_cjk_count = total_chars - cjk_count

    cjk_tokens = cjk_count * 0.8
    latin_tokens = non_cjk_count * 0.25

    return int(cjk_tokens + latin_tokens)
