"""stdio 协议级冒烟：用官方 mcp SDK 的 client over stdio 驱动本 server。

证明本项目作为真实 MCP server 在传输层可用（而非只直调 tools.call）。

流程: 子进程拉起 server -> initialize -> tools/list(断言 4 个) -> call health -> 打印。

用法:
    python scripts/smoke_stdio.py
依赖: 已 `pip install -e .`；health 会真打 ${APP_BASE_URL}，需可达平台。
退出码: 0 = 通过, 1 = 失败。
"""

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

CORE_TOOLS = {"list_logs", "get_job", "health", "chat_query"}
GATEWAY_READ_TOOLS = {
    "gateway_observability", "gateway_info", "gateway_prompts",
    "gateway_redteam_report", "gateway_supply_chain_report",
    "gateway_pentest_report", "gateway_supply_chain_samples",
}
EXPECTED_TOOLS = CORE_TOOLS | GATEWAY_READ_TOOLS  # 4 核心 + 7 网关只读 = 11


async def _run() -> int:
    params = StdioServerParameters(command=sys.executable, args=["-m", "ai_log_mcp.server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("[1] initialize: OK")

            listed = await session.list_tools()
            names = {t.name for t in listed.tools}
            print(f"[2] tools/list: {len(names)} tools {sorted(names)}")
            if names != EXPECTED_TOOLS:
                missing = EXPECTED_TOOLS - names
                extra = names - EXPECTED_TOOLS
                print(f"    FAIL: expected {len(EXPECTED_TOOLS)} | missing={sorted(missing)} extra={sorted(extra)}", file=sys.stderr)
                return 1

            result = await session.call_tool("health", {})
            text = result.content[0].text if result.content else "(empty)"
            print(f"[3] call_tool(health): {text}")

    print("SMOKE OK")
    return 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
