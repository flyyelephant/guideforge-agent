"""Text/Markdown/UDN loader for local knowledge file ingestion."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Optional

from src.core.types import Document
from src.libs.loader.base_loader import BaseLoader


class TextLoader(BaseLoader):
    """Load UTF-8-ish text files into the modular ingestion pipeline."""

    def __init__(self, encoding_candidates: Optional[list[str]] = None):
        self.encoding_candidates = encoding_candidates or [
            "utf-8",
            "utf-8-sig",
            "gb18030",
            "latin-1",
        ]

    def load(self, file_path: str | Path) -> Document:
        path = self._validate_file(file_path)
        text = self._read_text(path)
        doc_hash = self._compute_file_hash(path)
        suffix = path.suffix.lower().lstrip(".") or "text"

        metadata: Dict[str, Any] = {
            "source_path": str(path),
            "doc_type": suffix,
            "doc_hash": doc_hash,
            "name": path.name,
        }

        title = self._extract_title(text, path.stem)
        if title:
            metadata["title"] = title

        return Document(
            id=f"doc_{doc_hash[:16]}",
            text=text,
            metadata=metadata,
        )

    def _read_text(self, path: Path) -> str:
        last_error: Optional[Exception] = None
        for encoding in self.encoding_candidates:
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError as exc:
                last_error = exc
        if last_error is not None:
            raise RuntimeError(f"failed to decode text file {path}: {last_error}") from last_error
        return path.read_text(encoding="utf-8", errors="ignore")

    @staticmethod
    def _compute_file_hash(path: Path) -> str:
        sha256 = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def _extract_title(text: str, fallback: str) -> str:
        for raw_line in text.splitlines()[:30]:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("#"):
                return line.lstrip("#").strip() or fallback
            return line[:200]
        return fallback
