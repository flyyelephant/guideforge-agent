"""Entry point for the Smart UE Assistant MCP Server."""
import os
import sys


def main():
    from .server import mcp
    from .tools import (
        # 资产查询（只读）
        asset_query,
        # 资产写操作
        asset_write,
        # 其他工具
        project, world, actors, viewport, python, editor, knowledge, materials,
        context, properties, blueprints, screenshots, events,
        build, rag, batch_ops, scene_analysis,
    )
    mode = os.environ.get("SMART_UE_MODE", "stdio")
    if mode == "http":
        _run_http()
    elif mode == "both":
        _run_both(mcp)
    else:
        mcp.run(transport="stdio")


def _run_http():
    try:
        from .http_server import run_http_server
        run_http_server()
    except ImportError:
        print("http_server not implemented", file=sys.stderr)
        sys.exit(1)


def _run_both(mcp):
    import threading
    try:
        from .http_server import run_http_server
        threading.Thread(target=run_http_server, daemon=True).start()
    except ImportError:
        pass
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
