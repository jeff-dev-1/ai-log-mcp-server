"""MCP tool 定义与分发。

边界（CLAUDE.md / DESIGN.md §3）：
- 每个 tool 可追溯到 DESIGN §3.1 的一行；inputSchema 取自现查的 openapi。
- tool 只做「组装请求 → rest_client 调 REST → 透传响应」。
- 非 2xx 按 DESIGN §4 返回结构化错误（status + body），不吞错、不重试登录。
"""

import mcp.types as types

from . import rest_client

# ── tool 定义（schema 源自 ${APP_BASE_URL}/openapi.json）───────────────────────
TOOLS: list[types.Tool] = [
    types.Tool(
        name="list_logs",
        description="列出最近的日志/任务（GET /logs）。",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "最多返回条数（可选，对应 query 参数 limit）"},
            },
            "required": [],
        },
    ),
    types.Tool(
        name="get_job",
        description="按任务 ID 获取日志分析任务的明细/结果（GET /logs/jobs/{job_id}）。",
        inputSchema={
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "任务 ID（对应 path 参数 job_id）"},
            },
            "required": ["job_id"],
        },
    ),
    types.Tool(
        name="health",
        description="平台健康/连通检查（GET /health）。",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
]


def _error(status: int, body) -> dict:
    """DESIGN §4 结构化错误。"""
    return {"error": True, "status": status, "body": body}


def call(name: str, arguments: dict):
    """分发并执行 tool，返回透传 payload 或结构化错误。

    注意：这是同步函数（内部走 httpx.Client）。server 侧用线程池调用以不阻塞事件循环。
    """
    arguments = arguments or {}

    if name == "list_logs":
        params = {}
        if arguments.get("limit") is not None:
            params["limit"] = arguments["limit"]
        status, body = rest_client.request_json("GET", "/logs", params=params or None)
    elif name == "get_job":
        job_id = arguments["job_id"]
        status, body = rest_client.request_json("GET", f"/logs/jobs/{job_id}")
    elif name == "health":
        status, body = rest_client.request_json("GET", "/health")
    else:
        raise ValueError(f"unknown tool: {name}")

    if not 200 <= status < 300:
        return _error(status, body)
    return body
