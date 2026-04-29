"""File tools with a minimal runtime boundary."""

from __future__ import annotations

from pathlib import Path

from ..runtime.artifacts import ArtifactManager
from ..runtime.types import ToolResult
from .base import BaseTool


def _resolve_runtime_path(state, relative_path: str) -> Path:
    workdir = Path(state.runtime["workdir"]).resolve()
    output_dir = Path(state.runtime["output_dir"]).resolve()
    candidate = (output_dir / relative_path).resolve()

    allowed_roots = [workdir, output_dir]
    if not any(str(candidate).startswith(str(root)) for root in allowed_roots):
        raise ValueError(f"Path '{relative_path}' escapes the allowed runtime roots.")
    return candidate


class ReadFileTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="read_file",
            description="Read a text file from the runtime workdir/output dir.",
            input_schema={"path": "Relative file path"},
        )

    def invoke(self, state, args):
        path = _resolve_runtime_path(state, args["path"])
        if not path.exists():
            return ToolResult.fail(tool_name=self.name, error=f"File not found: {path.name}")
        return ToolResult.ok(tool_name=self.name, content=path.read_text(encoding="utf-8"))


class WriteFileTool(BaseTool):
    def __init__(self, artifact_manager: ArtifactManager) -> None:
        super().__init__(
            name="write_file",
            description="Write a text file into the output directory.",
            input_schema={"path": "Relative output file path", "content": "File content"},
        )
        self.artifact_manager = artifact_manager

    def invoke(self, state, args):
        path = _resolve_runtime_path(state, args["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args["content"], encoding="utf-8")
        artifact = self.artifact_manager.record_file(path, kind="text")
        return ToolResult.ok(
            tool_name=self.name,
            content=f"Wrote file to {path}",
            artifacts=[artifact],
        )


class PresentFileTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="present_file",
            description="Show a preview of a generated file and keep it in the artifact list.",
            input_schema={"path": "Relative output file path"},
        )

    def invoke(self, state, args):
        path = _resolve_runtime_path(state, args["path"])
        if not path.exists():
            return ToolResult.fail(tool_name=self.name, error=f"Cannot present missing file: {path.name}")
        preview = path.read_text(encoding="utf-8")[:400]
        return ToolResult.ok(tool_name=self.name, content=f"Presenting {path.name}:\n{preview}")

