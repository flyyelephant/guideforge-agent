"""Minimal FastAPI web entrypoint for the lightweight agent runtime."""

from __future__ import annotations

import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from backend.app.bootstrap import build_agent, build_state, get_project_root, get_runtime_paths
from backend.app.workflows.specs import get_workflow_spec

app = FastAPI(title="deerflow-lite-agent", version="0.1.0")

_INDEX_HTML = (get_project_root() / "web" / "index.html").read_text(encoding="utf-8")
_AGENT, _WORKDIR, _OUTPUT_DIR = build_agent(user_id="web-user")
_SESSIONS: dict[str, Any] = {}


def _read_text_artifact(path: Path) -> str:
    for encoding in ('utf-8-sig', 'utf-8', 'gb18030'):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding='utf-8', errors='replace')


class ChatRequest(BaseModel):
    user_input: str
    session_id: str | None = None


def _get_or_create_session(session_id: str | None):
    if session_id and session_id in _SESSIONS:
        return session_id, _SESSIONS[session_id]

    new_session_id = session_id or secrets.token_hex(8)
    state = build_state(session_id=new_session_id, user_id="web-user")
    _SESSIONS[new_session_id] = state
    return new_session_id, state


def _reset_transient_state(state) -> None:
    # Keep message history and memory, but clear request-scoped presentation fields
    # so the Web UI reflects the current turn instead of stale debug metadata.
    state.set_task(None, [])
    state.set_response_mode(None)
    state.set_deliverable(None)
    state.set_retrieved_sources([])
    state.context.pop("planner_debug", None)


def _artifact_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    path = Path(artifact["path"])
    return {
        "name": path.name,
        "path": str(path),
        "kind": artifact.get("kind", "text"),
        "view_url": f"/api/artifacts/{path.name}",
        "download_url": f"/api/artifacts/{path.name}/download",
    }


def _state_payload(state, response) -> dict[str, Any]:
    task_type = state.task_type
    references = list(state.retrieved_sources)
    return {
        "status": response.status,
        "output_text": response.output_text,
        "clarification_question": response.clarification_question,
        "task_type": task_type,
        "response_mode": state.response_mode,
        "workflow_hit": get_workflow_spec(task_type or "") is not None,
        "tool_outputs": list(response.tool_outputs),
        "references": references,
        "artifacts": [_artifact_payload(item) for item in response.artifacts],
        "planner_debug": dict(state.context.get("planner_debug", {})),
    }


def _list_artifacts() -> list[dict[str, Any]]:
    _, output_dir = get_runtime_paths()
    artifacts: list[dict[str, Any]] = []
    for path in sorted(output_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
        if not path.is_file():
            continue
        artifacts.append(
            {
                "name": path.name,
                "path": str(path),
                "size": path.stat().st_size,
                "updated_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                "view_url": f"/api/artifacts/{path.name}",
                "download_url": f"/api/artifacts/{path.name}/download",
            }
        )
    return artifacts


def _resolve_artifact(filename: str) -> Path:
    _, output_dir = get_runtime_paths()
    path = (output_dir / filename).resolve()
    if path.parent != output_dir.resolve() or not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return path


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _INDEX_HTML


@app.post("/api/chat")
def chat(payload: ChatRequest) -> dict[str, Any]:
    user_input = payload.user_input.strip()
    if not user_input:
        raise HTTPException(status_code=400, detail="user_input cannot be empty")

    session_id, state = _get_or_create_session(payload.session_id)
    old_artifact_count = len(state.artifacts)
    _reset_transient_state(state)
    response = _AGENT.run(user_input, state)
    current_turn_artifacts = state.artifacts[old_artifact_count:]
    response.artifacts = current_turn_artifacts

    result = _state_payload(state, response)
    result["session_id"] = session_id
    result["messages"] = [
        {"role": item.role, "content": item.content, "metadata": item.metadata, "created_at": item.created_at}
        for item in state.messages
    ]
    return result


@app.get("/api/artifacts")
def list_artifacts() -> dict[str, Any]:
    return {"artifacts": _list_artifacts()}


@app.get("/api/artifacts/{filename}")
def view_artifact(filename: str) -> dict[str, Any]:
    path = _resolve_artifact(filename)
    text = _read_text_artifact(path) if path.suffix.lower() in {".md", ".txt", ".json", ".log"} else "Preview unavailable for this file type."
    return {
        "name": path.name,
        "path": str(path),
        "content": text,
        "download_url": f"/api/artifacts/{path.name}/download",
    }


@app.get("/api/artifacts/{filename}/download")
def download_artifact(filename: str, download: bool = Query(default=True)):
    path = _resolve_artifact(filename)
    return FileResponse(path, filename=path.name, media_type="application/octet-stream")


if __name__ == "__main__":
    uvicorn.run("web_app:app", host="127.0.0.1", port=8000, reload=False)
