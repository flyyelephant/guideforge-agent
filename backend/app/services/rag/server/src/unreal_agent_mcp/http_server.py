"""HTTP server entry point for Slate UI — receives POST /chat, returns SSE stream."""

import logging
import os

logger = logging.getLogger(__name__)


def run_http_server():
    """启动 HTTP server，供 Slate UI 调用。阻塞运行。"""
    try:
        import uvicorn
        from .app import create_app
        app = create_app()
        port = int(os.environ.get("MCP_HTTP_PORT", "8765"))
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
    except ImportError:
        logger.error("uvicorn or fastapi not installed. Run: pip install fastapi uvicorn")
        raise