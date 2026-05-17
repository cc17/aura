"""In-memory file store for generated downloads (e.g. .docx exports)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class FileEntry:
    filename: str
    data: bytes
    content_type: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FileStore:
    MAX_ENTRIES = 100

    def __init__(self) -> None:
        self._files: dict[str, FileEntry] = {}

    def save(self, filename: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Store a file and return its unique ID."""
        if len(self._files) >= self.MAX_ENTRIES:
            # Evict the oldest entry
            oldest_id = min(self._files, key=lambda k: self._files[k].created_at)
            del self._files[oldest_id]

        file_id = uuid.uuid4().hex[:12]
        self._files[file_id] = FileEntry(
            filename=filename,
            data=data,
            content_type=content_type,
        )
        return file_id

    def get(self, file_id: str) -> FileEntry | None:
        return self._files.get(file_id)


# Module-level singleton
file_store = FileStore()
