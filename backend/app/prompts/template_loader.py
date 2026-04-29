"""Lightweight template loader for structured document outputs."""

from __future__ import annotations

from pathlib import Path

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def read_template(template_name: str) -> str:
    path = _TEMPLATE_DIR / f"{template_name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {template_name}")
    return path.read_text(encoding="utf-8")
