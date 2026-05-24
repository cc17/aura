"""Disk-backed file store for generated downloads (PPT, docx exports, etc.).

Files are written to AURA_FILES_DIR (default: ./generated_files/).
Metadata (filename, content_type, download_token) is stored as a sibling
.json file so the store survives server restarts.
"""

from __future__ import annotations

import json
import logging
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class FileEntry:
    filename: str
    content_type: str
    download_token: str
    data_path: Path
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def data(self) -> bytes:
        return self.data_path.read_bytes()


class FileStore:
    MAX_ENTRIES = 200

    def __init__(self, store_dir: str | None = None) -> None:
        dir_path = store_dir or getattr(settings, "files_dir", "./generated_files")
        self._dir = Path(dir_path)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._meta: dict[str, FileEntry] = {}
        self._load_existing()

    def _load_existing(self) -> None:
        count = 0
        for meta_path in self._dir.glob("*.json"):
            file_id = meta_path.stem
            data_path = self._dir / file_id
            if not data_path.exists():
                meta_path.unlink(missing_ok=True)
                continue
            try:
                info = json.loads(meta_path.read_text())
                self._meta[file_id] = FileEntry(
                    filename=info["filename"],
                    content_type=info["content_type"],
                    download_token=info["download_token"],
                    data_path=data_path,
                    created_at=datetime.fromisoformat(info["created_at"]),
                )
                count += 1
            except Exception:
                logger.warning("file_store: skipping corrupt metadata %s", meta_path)
        if count:
            logger.info("file_store: loaded %d existing files from %s", count, self._dir)

    def save(self, filename: str, data: bytes, content_type: str = "application/octet-stream") -> tuple[str, str]:
        """Store a file and return (file_id, download_token)."""
        if len(self._meta) >= self.MAX_ENTRIES:
            oldest_id = min(self._meta, key=lambda k: self._meta[k].created_at)
            self._evict(oldest_id)

        file_id = uuid.uuid4().hex[:12]
        download_token = secrets.token_urlsafe(16)
        data_path = self._dir / file_id
        meta_path = self._dir / f"{file_id}.json"

        data_path.write_bytes(data)
        meta_path.write_text(json.dumps({
            "filename": filename,
            "content_type": content_type,
            "download_token": download_token,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }))

        self._meta[file_id] = FileEntry(
            filename=filename,
            content_type=content_type,
            download_token=download_token,
            data_path=data_path,
        )
        logger.debug("file_store: saved %s (%d bytes) id=%s", filename, len(data), file_id)
        return file_id, download_token

    def get(self, file_id: str) -> FileEntry | None:
        return self._meta.get(file_id)

    def _evict(self, file_id: str) -> None:
        (self._dir / file_id).unlink(missing_ok=True)
        (self._dir / f"{file_id}.json").unlink(missing_ok=True)
        self._meta.pop(file_id, None)


file_store = FileStore()
