"""Token counting using tiktoken (cl100k_base).

The ~10% deviation from Doubao's actual tokenizer is within our safety margin.
We compute once at write time and store the count in the DB.
"""

from __future__ import annotations

import tiktoken

_encoding: tiktoken.Encoding | None = None


def _get_encoding() -> tiktoken.Encoding:
    global _encoding
    if _encoding is None:
        _encoding = tiktoken.get_encoding("cl100k_base")
    return _encoding


def count_tokens(text: str | None) -> int:
    """Return the number of tokens in the given text."""
    if not text:
        return 0
    return len(_get_encoding().encode(text))


def count_message_tokens(role: str, content: str | None) -> int:
    """Estimate tokens for a chat message (role overhead + content).

    Adds ~4 tokens for message framing (role, separators).
    """
    return 4 + count_tokens(content)
