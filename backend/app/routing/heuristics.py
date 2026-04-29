"""Routing heuristics for non-workflow requests and response-mode policy.

These helpers keep the main agent focused on orchestration while preserving the
current lightweight heuristic style.
"""

from __future__ import annotations


def classify_response_mode(user_input: str, task_type: str | None, *, default_workflow_mode: str | None = None) -> str:
    lower = user_input.lower()
    deliverable_markers = [
        "markdown", "document", "doc", "file", "deliverable",
        "文档", "文件", "交付", "生成文件", "输出为", "写成",
        "proposal doc", "tutorial doc", "workflow doc",
    ]
    structured_markers = [
        "plan", "steps", "phase", "outline", "recommend", "analysis", "risk",
        "workflow", "proposal", "tutorial", "how should",
        "建议", "步骤", "阶段", "风险", "分析", "梳理", "方案", "流程", "教程",
    ]
    question_markers = ["what", "how", "why", "?", "什么", "如何", "怎么", "为什么", "？"]

    if any(marker in lower or marker in user_input for marker in deliverable_markers):
        return "deliverable_file"

    if task_type == "proposal_generation":
        return default_workflow_mode or "structured_chat"

    if task_type in {"tutorial_writing", "workflow_support"}:
        has_question = any(marker in lower or marker in user_input for marker in question_markers)
        has_structure = any(marker in lower or marker in user_input for marker in structured_markers)
        if has_question and not has_structure:
            return "direct_answer"
        return default_workflow_mode or "structured_chat"

    if any(marker in lower or marker in user_input for marker in question_markers):
        return "direct_answer"
    if any(marker in lower or marker in user_input for marker in structured_markers):
        return "structured_chat"
    return "direct_answer"


def needs_general_clarification(user_input: str) -> bool:
    stripped = user_input.strip().lower()
    ambiguous = {"help me", "do this", "make something", "帮我搞一下", "帮我看看"}
    if stripped in ambiguous:
        return True
    return len(stripped) < 8 and ("?" in stripped or "帮" in stripped)


def general_clarification_question() -> str:
    return "Please share the goal, constraints, or expected output."


def needs_workflow_clarification(user_input: str) -> bool:
    stripped = user_input.strip()
    if len(stripped) < 14:
        return True
    scope_markers = ["blueprint", "widget", "editor", "ui", "gameplay", "asset", "pipeline", "workflow", "proposal", "教程", "方案", "流程", "测试"]
    return not any(marker in stripped.lower() or marker in stripped for marker in scope_markers)


def should_use_answer_ue_docs(user_input: str) -> bool:
    lower = user_input.lower()
    ue_markers = ["ue", "unreal", "blueprint", "widget", "editor", "gameplay", "蓝图", "编辑器"]
    question_markers = ["what", "how", "why", "?", "什么", "如何", "怎么", "为什么", "？"]
    return any(marker in lower or marker in user_input for marker in ue_markers) and any(marker in lower or marker in user_input for marker in question_markers)


def needs_task_split(user_input: str) -> bool:
    lower = user_input.lower()
    keywords = ["analyze", "steps", "plan", "risk", "拆", "步骤", "风险"]
    return any(word in lower or word in user_input for word in keywords) and len(user_input) > 18


def build_subtasks(user_input: str) -> list[str]:
    return [
        f"Clarify the goal: {user_input}",
        f"Outline an implementation approach: {user_input}",
        f"Summarize risks and next steps: {user_input}",
    ]


def needs_file_output(user_input: str) -> bool:
    lower = user_input.lower()
    markers = ["markdown", "md", "write file", "save this", "写成文件"]
    return any(marker in lower or marker in user_input for marker in markers)


def should_use_search(user_input: str) -> bool:
    lower = user_input.lower()
    markers = ["search", "lookup", "find", "查", "搜索", "调研"]
    return any(marker in lower or marker in user_input for marker in markers)


def should_use_rag(user_input: str) -> bool:
    lower = user_input.lower()
    markers = ["rag", "deerflow", "agent runtime", "prompt", "tool"]
    return any(marker in lower for marker in markers)
