"""Lightweight helpers for file-based skill assets.

This intentionally stays small. The goal is only to separate skill metadata and
body content from Python constants, not to recreate DeerFlow's full skill
parsing system.

Convention:
- `_meta.json` is the system-facing source of truth for skill metadata.
- `skill.md` front matter is only a lightweight, human-readable mirror.
- If the two ever diverge, prefer `_meta.json`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_skill_meta(skill_dir: Path) -> dict[str, Any]:
    meta_path = skill_dir / "_meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Skill metadata file is missing: {meta_path}")
    return json.loads(meta_path.read_text(encoding="utf-8"))


def read_skill_body(skill_dir: Path) -> str:
    body_path = skill_dir / "skill.md"
    if not body_path.exists():
        raise FileNotFoundError(f"Skill body file is missing: {body_path}")
    return body_path.read_text(encoding="utf-8").strip()
