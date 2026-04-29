"""Select skill prompt snippets based on request text, workflow metadata, and response mode."""

from __future__ import annotations

from pathlib import Path

from ..workflows.selector import resolve_workflow_intent
from ..workflows.specs import get_workflow_spec
from .parser import read_skill_body, read_skill_meta
from .templates import SKILL_TEMPLATES

_RESPONSE_MODE_HINTS = {
    "direct_answer": "[Response mode hint]\n- The user wants a concise direct answer, so do not force file delivery or excessive formatting.",
    "structured_chat": "[Response mode hint]\n- The user wants a structured chat answer, so organize the output clearly in chat without forcing file generation.",
    "deliverable_file": "[Response mode hint]\n- The user explicitly wants a formal deliverable, so organize content for template-based file output.",
}

_SKILLS_ROOT = Path(__file__).resolve().parent


def _resolve_skill_dir(skill_key: str) -> Path | None:
    task_name = skill_key.removesuffix("_skill")
    candidate = _SKILLS_ROOT / task_name
    return candidate if candidate.exists() and candidate.is_dir() else None


def _load_skill_section(skill_key: str) -> str | None:
    skill_dir = _resolve_skill_dir(skill_key)
    if skill_dir is None:
        # Legacy fallback: keep the runtime working if a file-based skill has
        # not been created yet for this key.
        return SKILL_TEMPLATES.get(skill_key)

    try:
        meta = read_skill_meta(skill_dir)
        body = read_skill_body(skill_dir)
    except FileNotFoundError:
        # Legacy fallback: during migration, prefer continuity over failure.
        # This fallback can be removed once all production skills are fully
        # file-based and validated.
        return SKILL_TEMPLATES.get(skill_key)

    if meta.get("key") != skill_key:
        # Legacy fallback: if metadata does not match the expected key, do not
        # trust the on-disk asset yet.
        return SKILL_TEMPLATES.get(skill_key)

    return body or SKILL_TEMPLATES.get(skill_key)


def list_available_skills() -> list[dict[str, str]]:
    """Return lightweight metadata for file-based skills.

    This is intended for debugging and local management, not as a heavy runtime
    registry. Only file-based skills with a readable `_meta.json` are listed.
    """
    skills: list[dict[str, str]] = []
    for skill_dir in sorted(path for path in _SKILLS_ROOT.iterdir() if path.is_dir() and not path.name.startswith("__")):
        try:
            meta = read_skill_meta(skill_dir)
        except FileNotFoundError:
            continue

        key = str(meta.get("key", "")).strip()
        if not key:
            continue

        skills.append(
            {
                "key": key,
                "name": str(meta.get("name", "")).strip(),
                "description": str(meta.get("description", "")).strip(),
                "path": str(skill_dir.resolve()),
            }
        )
    return skills


def select_skill_sections(user_input: str, task_type: str | None = None, response_mode: str | None = None) -> list[str]:
    sections: list[str] = []

    spec = get_workflow_spec(task_type) if task_type else None
    if spec is None:
        match = resolve_workflow_intent(user_input)
        spec = match.spec if match else None

    if spec:
        section = _load_skill_section(spec.skill_key)
        if section:
            sections.append(section)

    if response_mode in _RESPONSE_MODE_HINTS:
        sections.append(_RESPONSE_MODE_HINTS[response_mode])

    return sections
