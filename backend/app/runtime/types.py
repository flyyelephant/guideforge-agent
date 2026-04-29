"""Shared runtime datatypes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]


@dataclass
class ModelDecision:
    mode: str
    response_text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    subtasks: list[str] = field(default_factory=list)
    rationale: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    tool_name: str
    success: bool
    content: str
    error: str | None = None
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(
        cls,
        *,
        tool_name: str,
        content: str,
        artifacts: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ToolResult":
        return cls(
            tool_name=tool_name,
            success=True,
            content=content,
            artifacts=artifacts or [],
            metadata=metadata or {},
        )

    @classmethod
    def fail(cls, *, tool_name: str, error: str) -> "ToolResult":
        return cls(tool_name=tool_name, success=False, content="", error=error)


@dataclass
class AgentResponse:
    status: str
    output_text: str
    clarification_question: str | None = None
    tool_outputs: list[str] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
