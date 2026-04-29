"""Minimal runnable entrypoint for the lightweight agent runtime."""

from __future__ import annotations

import argparse

from backend.app.bootstrap import build_agent, build_state
from backend.app.runtime.types import AgentResponse


def print_response(response: AgentResponse) -> None:
    print("=" * 72)
    print(f"Status: {response.status}")
    if response.clarification_question:
        print(f"Clarification: {response.clarification_question}")
    print("Response:")
    print(response.output_text)
    if response.tool_outputs:
        print("\nTool Outputs:")
        for item in response.tool_outputs:
            print(f"- {item}")
    if response.artifacts:
        print("\nArtifacts:")
        for artifact in response.artifacts:
            print(f"- {artifact['path']} ({artifact['kind']})")


def build_cli_runtime() -> tuple:
    agent, _, _ = build_agent(user_id="demo-user")
    state = build_state(session_id="demo-session", user_id="demo-user")
    return agent, state


def run_demo() -> None:
    agent, state = build_cli_runtime()

    examples = [
        "What is Blueprint in Unreal Engine?",
        "Help me narrow a vague request",
        "Write a Blueprint testing tutorial and generate markdown",
        "Give me an Unreal Editor testing proposal",
        "Create a Blueprint workflow document",
    ]

    for prompt in examples:
        print(f"\nUser: {prompt}")
        response = agent.run(prompt, state)
        print_response(response)


def run_interactive() -> None:
    agent, state = build_cli_runtime()
    print("Lightweight Agent Runtime. Type 'exit' to quit.")
    while True:
        user_input = input("\nYou: ").strip()
        if not user_input or user_input.lower() in {"exit", "quit"}:
            break
        response = agent.run(user_input, state)
        print_response(response)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the lightweight DeerFlow-inspired agent runtime.")
    parser.add_argument("--interactive", action="store_true", help="Start an interactive session instead of the canned demo.")
    args = parser.parse_args()

    if args.interactive:
        run_interactive()
    else:
        run_demo()


if __name__ == "__main__":
    main()
