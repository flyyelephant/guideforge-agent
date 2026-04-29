"""Factory for creating the main agent runtime."""

from __future__ import annotations

from pathlib import Path

from .decision_guardrails import DecisionGuardrails
from .llm_planner import LLMPlanner
from .main_agent import HeuristicModel, MainAgent
from ..memory.store import MemoryStore
from ..middleware.base import MiddlewareManager
from ..middleware.clarification import ClarificationMiddleware
from ..middleware.summarization import SummarizationMiddleware
from ..middleware.tool_error import ToolErrorMiddleware
from ..runtime.artifacts import ArtifactManager
from ..runtime.executor import SerialTaskExecutor
from ..tools.registry import ToolRegistry, get_available_tools


def create_main_agent(*, workdir: Path, output_dir: Path, user_id: str) -> MainAgent:
    workdir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    artifact_manager = ArtifactManager(output_dir=output_dir)
    memory_store = MemoryStore(workdir / 'memory.json')
    registry = ToolRegistry()
    task_executor = SerialTaskExecutor(tool_registry=registry)

    for tool in get_available_tools(
        artifact_manager=artifact_manager,
        task_executor=task_executor,
        enabled_tools=None,
    ):
        registry.register(tool)

    middleware_manager = MiddlewareManager(
        middlewares=[
            ToolErrorMiddleware(),
            SummarizationMiddleware(max_messages=10),
            ClarificationMiddleware(),
        ]
    )

    fallback_model = HeuristicModel()
    planner = LLMPlanner()
    guardrails = DecisionGuardrails(fallback_model=fallback_model)

    return MainAgent(
        planner=planner,
        fallback_model=fallback_model,
        guardrails=guardrails,
        tool_registry=registry,
        middleware_manager=middleware_manager,
        memory_store=memory_store,
    )
