"""FastAPI app — /chat endpoint backed by docs RAG answer generation."""

import json
import logging
import sys
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

# `rag/` lives beside `src/`, so inject the server root once here and keep
# the HTTP layer thin. Retrieval/generation stay inside `rag.service`.
_SERVER_ROOT = Path(__file__).parent.parent.parent
if str(_SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVER_ROOT))

from rag.service import get_rag_service  # noqa: E402


def create_app() -> FastAPI:
    app = FastAPI(title="SmartUEAssistant HTTP Gateway")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["POST", "GET"],
        allow_headers=["*"],
    )

    @app.get("/", response_class=HTMLResponse)
    async def home() -> str:
        """Minimal browser chat page for validating the docs RAG pipeline."""
        return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SmartUEAssistant Chat</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f1e8;
      --panel: #fffaf1;
      --ink: #18222d;
      --muted: #5f6b76;
      --line: #d9d0bf;
      --accent: #0f6c5c;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      background:
        radial-gradient(circle at top left, #fff6d7, transparent 30%),
        linear-gradient(135deg, #f0ece2, #f7f4ee 45%, #e9f0eb);
      color: var(--ink);
    }
    .shell {
      width: min(900px, calc(100vw - 32px));
      margin: 32px auto;
      padding: 20px;
      background: rgba(255, 250, 241, 0.92);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 20px 50px rgba(24, 34, 45, 0.08);
      backdrop-filter: blur(8px);
    }
    h1 { margin: 0 0 8px; font-size: 24px; }
    p { margin: 0 0 16px; color: var(--muted); }
    #messages {
      min-height: 360px;
      max-height: 60vh;
      overflow-y: auto;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fffdf8;
    }
    .msg {
      white-space: pre-wrap;
      padding: 12px 14px;
      border-radius: 12px;
      margin: 10px 0;
      line-height: 1.55;
    }
    .user { background: #e5f4ef; margin-left: 60px; }
    .assistant { background: #f2ede3; margin-right: 60px; }
    .sources {
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px dashed var(--line);
      color: var(--muted);
      font-size: 13px;
    }
    .row { display: flex; gap: 12px; margin-top: 16px; }
    textarea {
      flex: 1;
      min-height: 96px;
      resize: vertical;
      padding: 12px;
      border-radius: 12px;
      border: 1px solid var(--line);
      font: inherit;
      background: #fffdf8;
    }
    button {
      width: 132px;
      border: 0;
      border-radius: 12px;
      background: var(--accent);
      color: white;
      font: inherit;
      cursor: pointer;
    }
    button:disabled { opacity: 0.6; cursor: wait; }
  </style>
</head>
<body>
  <main class="shell">
    <h1>SmartUEAssistant</h1>
    <p>这里直接走当前项目的 docs RAG 回答链。输入 UE 问题后会调用 <code>POST /chat</code>。</p>
    <section id="messages"></section>
    <div class="row">
      <textarea id="input" placeholder="例如：Low Level Tests 是什么？"></textarea>
      <button id="send">发送</button>
    </div>
  </main>
  <script>
    const messagesEl = document.getElementById('messages');
    const inputEl = document.getElementById('input');
    const sendEl = document.getElementById('send');
    const history = [];

    function append(role, content, sources=[]) {
      const node = document.createElement('div');
      node.className = `msg ${role}`;
      const body = document.createElement('div');
      body.textContent = content;
      node.appendChild(body);
      if (role === 'assistant' && Array.isArray(sources) && sources.length) {
        const sourcesNode = document.createElement('div');
        sourcesNode.className = 'sources';
        const lines = ['参考来源：'];
        for (const [index, item] of sources.entries()) {
          lines.push(`[${index + 1}] ${item.name}`);
          if (item.path) lines.push(`    ${item.path}`);
        }
        sourcesNode.textContent = lines.join('\\n');
        node.appendChild(sourcesNode);
      }
      messagesEl.appendChild(node);
      messagesEl.scrollTop = messagesEl.scrollHeight;
      return node;
    }

    async function send() {
      const message = inputEl.value.trim();
      if (!message) return;
      append('user', message);
      inputEl.value = '';
      sendEl.disabled = true;
      const assistantNode = append('assistant', '思考中...');
      try {
        const response = await fetch('/chat', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ message, history, scene_context: '' }),
        });
        const data = await response.json();
        assistantNode.remove();
        const finalNode = append('assistant', data.response || '[empty]', data.sources || []);
        history.push({ role: 'user', content: message });
        history.push({ role: 'assistant', content: data.response || '[empty]' });
      } catch (error) {
        assistantNode.textContent = `[ERR] ${error}`;
      } finally {
        sendEl.disabled = false;
      }
    }

    sendEl.addEventListener('click', send);
    inputEl.addEventListener('keydown', (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        send();
      }
    });
  </script>
</body>
</html>"""

    @app.post("/chat")
    async def chat(request: Request):
        """接收 Slate 的消息，转发给 Claude API，返回 SSE 流。"""
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        user_message = body.get("message", "")
        history = body.get("history", [])
        scene_context = body.get("scene_context", "")

        if not user_message:
            return JSONResponse({"error": "Missing message"}, status_code=400)

        accept = request.headers.get("Accept", "")
        if "text/event-stream" in accept:
            return StreamingResponse(
                _stream_response(user_message, history, scene_context),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            # Non-SSE callers, including the browser debug page, get structured
            # JSON so the answer text and its sources can be rendered separately.
            service = get_rag_service()
            answer_response = await service.answer_docs(
                user_message,
                history=history,
                scene_context=scene_context,
            )
            payload = json.dumps(
                {
                    "response": answer_response.answer,
                    "sources": [
                        {"name": item.name, "path": item.path, "score": item.score}
                        for item in answer_response.sources
                    ],
                    "error": answer_response.error,
                },
                ensure_ascii=False,
            )
            return Response(
                content=payload.encode("utf-8"),
                media_type="application/json; charset=utf-8",
            )

    return app


async def _stream_response(
    message: str,
    history: list,
    scene_context: str,
) -> AsyncGenerator[str, None]:
    """Generate a grounded docs answer and emit it as SSE chunks."""
    try:
        service = get_rag_service()
        answer_response = await service.answer_docs(
            message,
            history=history,
            scene_context=scene_context,
        )
        for text in _chunk_text(answer_response.answer):
            payload = json.dumps({"content": text}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error("Docs answer pipeline failed: %s", e)
        error_payload = json.dumps({"content": f"[ERR:SERVER] RAG 回答失败：{str(e)}"}, ensure_ascii=False)
        yield f"data: {error_payload}\n\n"
        yield "data: [DONE]\n\n"


def _chunk_text(text: str, chunk_size: int = 120) -> list[str]:
    """Split a final answer into stable SSE-sized pieces for the UI."""
    if not text:
        return [""]
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
