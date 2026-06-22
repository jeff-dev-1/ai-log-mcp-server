"""MCP server 入口：官方 mcp SDK + stdio 传输。

边界（见 CLAUDE.md / DESIGN.md）：
- 本文件只搭骨架，**不注册任何具体 tool**。
- tool ↔ REST 端点映射当前为 _TBD_，其填充是 WORKFLOW.md 阶段 1 的第一步，
  早于任何 tool 代码。届时在 list_tools / call_tool 里按 DESIGN.md 映射表实现。
"""

import asyncio
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

from . import tools
from .config import get_base_url

server = Server("ai-log-mcp")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """返回可用工具列表（来自 tools.TOOLS，schema 源自 openapi）。"""
    return tools.TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """分发到 tools.call；REST 调用走线程池以不阻塞事件循环。结果以 JSON 文本透传。"""
    result = await asyncio.to_thread(tools.call, name, arguments)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    return [types.TextContent(type="text", text=text)]


async def _run() -> None:
    # 触发一次配置读取，便于启动期暴露明显的配置问题（不发网络请求）。
    _ = get_base_url()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
