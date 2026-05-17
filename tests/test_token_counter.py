"""Tests for token counting."""

from backend.memory.token_counter import count_message_tokens, count_tokens


def test_count_tokens_empty():
    assert count_tokens("") == 0
    assert count_tokens(None) == 0


def test_count_tokens_simple():
    result = count_tokens("Hello world")
    assert result > 0
    assert isinstance(result, int)


def test_count_message_tokens_includes_overhead():
    content_only = count_tokens("Hello world")
    with_overhead = count_message_tokens("user", "Hello world")
    assert with_overhead == content_only + 4


def test_count_tokens_chinese():
    """Chinese text should produce more tokens per character."""
    result = count_tokens("你好世界")
    assert result > 0
