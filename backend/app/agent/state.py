"""State primitives used by the lightweight runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Message:
    """A simple chat message structure."""

    role: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class AgentState:
    """Layered runtime state.

    The explicit workflow fields keep business-state separate from raw messages.
    This mirrors the DeerFlow idea that runtime state should hold more than chat
    history once the agent starts producing structured deliverables.
    """

    messages: list[Message] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    runtime: dict[str, Any] = field(default_factory=dict)
    task_type: str | None = None
    response_mode: str | None = None
    plan: list[str] = field(default_factory=list)
    deliverable: dict[str, Any] | None = None
    retrieved_sources: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def new_session(
        cls,
        *,
        session_id: str,
        user_id: str,
        workdir: str,
        output_dir: str,
    ) -> "AgentState":
        return cls(
            context={
                "conversation_summary": "",
                "last_user_intent": "",
                "memory_notes": "",
            },
            runtime={
                "session_id": session_id,
                "user_id": user_id,
                "workdir": workdir,
                "output_dir": output_dir,
                "accessible_roots": [workdir, output_dir],
            },
        )

    def add_message(self, role: str, content: str, **metadata: Any) -> None:
        self.messages.append(Message(role=role, content=content, metadata=metadata))

    def add_artifact(self, artifact: dict[str, Any]) -> None:
        self.artifacts.append(artifact)

    def set_task(self, task_type: str | None, plan: list[str] | None = None) -> None:
        self.task_type = task_type
        if plan is not None:
            self.plan = list(plan)

    def set_response_mode(self, response_mode: str | None) -> None:
        self.response_mode = response_mode

    def set_deliverable(self, deliverable: dict[str, Any] | None) -> None:
        self.deliverable = deliverable

    def set_retrieved_sources(self, sources: list[dict[str, Any]]) -> None:
        self.retrieved_sources = list(sources)
