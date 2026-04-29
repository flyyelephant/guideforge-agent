"""Artifact tracking."""

from __future__ import annotations

from pathlib import Path


class ArtifactManager:
    def __init__(self, *, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def record_file(self, path: Path, *, kind: str) -> dict[str, str]:
        return {"path": str(path), "kind": kind}
