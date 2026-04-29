"""Base tool interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..agent.state import AgentState
from ..runtime.types import ToolResult


@dataclass
class BaseTool(ABC):
    """Every runtime tool shares the same minimal shape."""

    name: str
    description: str
    input_schema: dict[str, str] = field(default_factory=dict)

    @abstractmethod
    def invoke(self, state: AgentState, args: dict[str, Any]) -> ToolResult:
        raise NotImplementedError

