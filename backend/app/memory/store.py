"""Minimal long-term memory store."""

from __future__ import annotations

import json
from pathlib import Path


class MemoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def _load(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, payload: dict) -> None:
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_memory(self, user_id: str) -> dict:
        payload = self._load()
        return payload.get(user_id, {"facts": [], "preferences": []})

    def update_memory(self, user_id: str, *, facts: list[str] | None = None, preferences: list[str] | None = None) -> dict:
        payload = self._load()
        user_memory = payload.setdefault(user_id, {"facts": [], "preferences": []})

        if facts:
            for fact in facts:
                if fact not in user_memory["facts"]:
                    user_memory["facts"].append(fact)
        if preferences:
            for preference in preferences:
                if preference not in user_memory["preferences"]:
                    user_memory["preferences"].append(preference)

        self._save(payload)
        return user_memory
