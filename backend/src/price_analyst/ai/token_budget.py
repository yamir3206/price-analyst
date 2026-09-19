"""Small deterministic token-budget helpers for compact Gemini requests."""

from __future__ import annotations

import math


def estimate_tokens(text: str) -> int:
    """Use a conservative character heuristic without a tokenizer dependency."""

    # Mixed Persian/Latin JSON commonly tokenizes more densely than four chars
    # per token; three keeps this boundary deliberately under the configured cap.
    return max(1, math.ceil(len(text) / 3))


def within_input_budget(text: str, max_tokens: int) -> bool:
    if max_tokens < 1:
        raise ValueError("max_tokens must be at least one")
    return estimate_tokens(text) <= max_tokens
