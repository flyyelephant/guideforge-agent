"""Shared bootstrap helpers for CLI and Web entrypoints.

The agent runtime remains the core. This module only centralizes project path,
agent, and session-state setup so multiple thin entrypoints can reuse the same
initialization logic.
"""

from __future__ import annotations

from pathlib import Path

from .agent.factory import create_main_agent
from .agent.state import AgentState


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def get_runtime_paths() -> tuple[Path, Path]:
    project_root = get_project_root()
    return project_root / "workspace", project_root / "outputs"


def build_agent(*, user_id: str = "demo-user"):
    workdir, output_dir = get_runtime_paths()
    agent = create_main_agent(
        workdir=workdir,
        output_dir=output_dir,
        user_id=user_id,
    )
    return agent, workdir, output_dir


def build_state(*, session_id: str, user_id: str = "demo-user") -> AgentState:
    workdir, output_dir = get_runtime_paths()
    return AgentState.new_session(
        session_id=session_id,
        user_id=user_id,
        workdir=str(workdir),
        output_dir=str(output_dir),
    )
