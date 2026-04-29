"""Small fallback response helpers.

These helpers keep content drafting separate from routing decisions so the
heuristic planner focuses on deciding, not on composing fallback text.
"""

from __future__ import annotations

from ..agent.state import AgentState


def build_fallback_direct_answer(user_input: str, state: AgentState) -> str:
    summary = state.context.get("conversation_summary") or "No summary yet."
    return (
        "This request does not need a tool call right now.\n"
        f"- Request: {user_input}\n"
        "- The runtime can still route to search, rag, file, or task tools when needed.\n"
        f"- Summary: {summary}"
    )


def build_fallback_document(user_input: str, state: AgentState) -> str:
    summary = state.context.get("conversation_summary") or "No summary yet."
    return "\n".join([
        "# Lightweight Agent Runtime Note",
        "",
        f"- User request: {user_input}",
        f"- Conversation summary: {summary}",
        "",
        "## Suggested Structure",
        "1. Main agent handles orchestration.",
        "2. Tools execute actions.",
        "3. Middleware owns cross-cutting control.",
        "4. State is layered into messages, context, artifacts, runtime, task_type, and response_mode.",
    ])
