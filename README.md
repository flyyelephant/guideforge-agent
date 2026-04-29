# deerflow-lite-agent

A lightweight Agent Runtime for developer-center workflows such as tutorial writing, proposal generation, and workflow support.

This project is inspired by the layering ideas in DeerFlow and LangGraph, but it is **not** a direct LangGraph implementation. It uses a custom runtime with:

- a lead agent / planner
- workflow specs
- tool registry
- file-based skills
- structured state
- local RAG integration
- artifact output and a minimal Web UI

## What it can do

Current core workflows:

- `tutorial_writing`
- `proposal_generation`
- `workflow_support`

Current response modes:

- `direct_answer`
- `structured_chat`
- `deliverable_file`

Current knowledge path:

- local Unreal Engine documentation
- bilingual query bridge for Chinese questions over mainly English docs
- retrieval-backed answers with lightweight references

## Project structure

```text
app.py                           # CLI entrypoint
web_app.py                       # FastAPI web entrypoint
web/                            # minimal web UI
outputs/                        # generated deliverables
workspace/                      # local runtime state
backend/app/
  agent/                        # planner, orchestration, prompt, state
  bootstrap.py                  # shared CLI/Web runtime bootstrap
  memory/                       # local memory store
  prompts/                      # prompt helpers and template loader
  runtime/                      # response/artifact/runtime types
  services/rag/                 # RAG adapter, query rewrite, terminology
  skills/                       # file-based skills (_meta.json + skill.md)
  templates/                    # deliverable templates
  tools/                        # executable tools and registry
  workflows/                    # workflow specs, renderers, tutorial authoring
```

## Requirements

Recommended:

- Python 3.11+
- Windows PowerShell or a normal terminal

The project currently uses:

- `fastapi`
- `uvicorn`
- `pydantic`
- `pyyaml`
- local RAG-related dependencies under `backend/app/services/rag/server/rag/requirements.txt`

## Install

At minimum, install the web/runtime dependencies you actually use in your environment.

Example:

```bash
pip install fastapi uvicorn pydantic pyyaml
pip install -r backend/app/services/rag/server/rag/requirements.txt
```

## Configuration

The project contains local RAG configuration files. Before running features that depend on model APIs, fill your own keys locally and **do not commit them**.

Primary config file:

- `backend/app/services/rag/server/rag/modular/config/settings.yaml`

Recommended local-only values:

- `llm.api_key`
- `embedding.api_key`
- `vision_llm.api_key` if you enable it

## Run

### CLI demo

```bash
python app.py
```

### CLI interactive mode

```bash
python app.py --interactive
```

### Web UI

```bash
python web_app.py
```

Then open:

```text
http://127.0.0.1:8000
```

## Web UI

The minimal Web UI supports:

- asking questions in the browser
- viewing the main answer
- inspecting `task_type` and `response_mode`
- viewing lightweight references
- viewing/downloading generated artifacts

## Tutorial writing behavior

`tutorial_writing` is currently tuned for:

- LLM-first tutorial authoring
- retrieval as optional support, not the tutorial backbone
- beginner-oriented structure
- Chinese output by default for Chinese user requests
- lightweight references instead of raw retrieval dumps

## Notes before publishing

Before uploading this repository to GitHub, check and remove or sanitize:

- API keys in config files
- generated outputs in `outputs/`
- local runtime data in `workspace/`
- caches, logs, vector DB files, and `__pycache__`

## Current status

This repository is best described as:

- a custom lightweight runtime
- inspired by DeerFlow / LangGraph layering ideas
- not a direct DeerFlow clone
- not a LangGraph StateGraph implementation
