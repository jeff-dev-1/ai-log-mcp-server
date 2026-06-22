"""MCP server 入口：官方 mcp SDK + stdio 传输。

边界（见 CLAUDE.md / DESIGN.md）：
- 本文件只搭骨架，**不注册任何具体 tool**。
- tool ↔ REST 端点映射当前为 _TBD_，其填充是 WORKFLOW.md 阶段 1 的第一步，
  早于任何 tool 代码。届时在 list_tools / call_tool 里按 DESIGN.md 映射表实现。
"""

import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

from .config import get_base_url

server = Server("ai-log-mcp")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """返回可用工具列表。

    当前为空 —— 具体 tool 的入参/出参 schema 必须来自 ${APP_BASE_URL}/openapi.json，
    不手抄、不臆造（CLAUDE.md 红线）。
    """
    # TODO(阶段 1): 拉取 openapi -> 按 DESIGN.md 映射表逐个生成 Tool。
    return []


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """工具调用分发位。骨架阶段无任何 tool，故一律报未知。"""
    # TODO(阶段 2): 组装请求 -> rest_client 调 REST -> 透传响应。
    raise ValueError(f"unknown tool: {name}")


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
