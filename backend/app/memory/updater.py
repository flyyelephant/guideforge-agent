"""Very small memory updater.

This v1 implementation only extracts a few explicit facts and preferences.
It is intentionally conservative so memory stays stable and easy to inspect.
"""

from __future__ import annotations

from .store import MemoryStore


def update_memory_from_text(store: MemoryStore, user_id: str, user_text: str) -> None:
    facts: list[str] = []
    preferences: list[str] = []
    lower = user_text.lower()

    if "i prefer " in lower:
        preferences.append(user_text[user_text.lower().index("i prefer ") + len("i prefer ") :].strip())
    if "我喜欢" in user_text:
        preferences.append(user_text.split("我喜欢", 1)[1].strip())
    if "我在做" in user_text:
        facts.append("Current work: " + user_text.split("我在做", 1)[1].strip())
    if "my project is" in lower:
        facts.append("Project: " + user_text[user_text.lower().index("my project is") + len("my project is") :].strip())

    if facts or preferences:
        store.update_memory(user_id, facts=facts, preferences=preferences)
