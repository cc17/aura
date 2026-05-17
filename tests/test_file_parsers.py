from __future__ import annotations

import pytest

from backend.utils.file_parsers import MAX_FILE_SIZE, extract_text


def test_extract_txt():
    text = extract_text("hello.txt", b"Hello, world!")
    assert text == "Hello, world!"


def test_extract_md():
    text = extract_text("readme.md", b"# Title\nContent")
    assert "# Title" in text
    assert "Content" in text


def test_extract_txt_utf8():
    content = "你好世界"
    text = extract_text("chinese.txt", content.encode("utf-8"))
    assert text == content


def test_unsupported_format():
    with pytest.raises(ValueError, match="Unsupported file format"):
        extract_text("image.png", b"\x89PNG")


def test_no_extension():
    with pytest.raises(ValueError, match="Unsupported file format"):
        extract_text("noext", b"data")


def test_file_too_large():
    data = b"x" * (MAX_FILE_SIZE + 1)
    with pytest.raises(ValueError, match="File too large"):
        extract_text("big.txt", data)


def test_file_at_limit():
    data = b"x" * MAX_FILE_SIZE
    text = extract_text("ok.txt", data)
    assert len(text) == MAX_FILE_SIZE
