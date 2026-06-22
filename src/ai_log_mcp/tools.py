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
    types.Tool(
        name="chat_query",
        description="对日志做 AI 问答/分析（POST /chat/query）。schema 源自 ChatRequest。",
        inputSchema={
            "type": "object",
            "properties": {
                "question": {"type": "string", "minLength": 1, "maxLength": 2000, "description": "问题（必填）"},
                "log_id": {"type": "string", "format": "uuid", "description": "限定某条日志（可选 UUID）"},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 20, "description": "检索条数（可选，平台默认 5）"},
                "backend": {"type": "string", "enum": ["deepseek", "qwen"], "description": "模型后端（可选，平台默认 deepseek）"},
                "scenario": {"type": "string", "maxLength": 80, "description": "场景：VS 综合 / 健康巡检 / SSL / 告警 / 慢根因 / 错误码 / 安全运营（可选）"},
            },
            "required": ["question"],
        },
    ),
]

# chat_query 允许透传给平台的字段（来自 ChatRequest）。
_CHAT_FIELDS = ("question", "log_id", "top_k", "backend", "scenario")

# ── 网关安全·只读（无参 GET，表驱动）─────────────────────────────────────────────
# {tool 名: (REST 路径, description)}。openapi 无输出 schema，description 是调用方选 tool 的唯一依据。
# 输出按现有模式原样透传；映射可追溯到 DESIGN.md §3.2。
GATEWAY_READS: dict[str, tuple[str, str]] = {
    "gateway_observability": (
        "/gateway/observability",
        "返回 AI 网关的可观测指标：调用总数/失败数/拦截数、错误率、token 用量与成本、p50/p95 延迟，以及按模型/后端/提供方的分布与近期调用。",
    ),
    "gateway_info": (
        "/gateway/info",
        "返回 AI 网关的配置信息：网关名称、当前 provider、默认后端、可用后端列表及其路由、guardrails 护栏配置。",
    ),
    "gateway_prompts": (
        "/gateway/prompts",
        "返回 AI 网关使用的提示词：系统提示词（system_prompts）与各场景提示词（scenario_prompts）。",
    ),
    "gateway_redteam_report": (
        "/gateway/redteam-report",
        "返回红队测试报告：整体通过率、按类别（注入/越狱/PII 等）的通过情况与失败用例明细。",
    ),
    "gateway_supply_chain_report": (
        "/gateway/supply-chain-report",
        "返回供应链安全检查报告：放行/拦截/待审批计数、被拦截与待审批条目，以及各依赖项的判定结果。",
    ),
    "gateway_pentest_report": (
        "/gateway/pentest-report",
        "返回渗透测试报告：测试目标、闸门（gate）结论、高/中危数量与各项安全发现（findings）。",
    ),
    "gateway_supply_chain_samples": (
        "/gateway/supply-chain/samples",
        "返回供应链检查的可选样本：是否启用、支持的市场（PyPI/npm/HuggingFace 等）与可供检查的示例样本。",
    ),
}

for _name, (_path, _desc) in GATEWAY_READS.items():
    TOOLS.append(
        types.Tool(
            name=_name,
            description=f"{_desc}（GET {_path}）",
            inputSchema={"type": "object", "properties": {}, "required": []},
        )
    )


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
    elif name == "chat_query":
        # 只透传 ChatRequest 定义的字段；缺省值交给平台，不在本地臆造。
        payload = {k: arguments[k] for k in _CHAT_FIELDS if arguments.get(k) is not None}
        status, body = rest_client.request_json("POST", "/chat/query", json=payload)
    elif name in GATEWAY_READS:
        path, _ = GATEWAY_READS[name]
        status, body = rest_client.request_json("GET", path)
    else:
        raise ValueError(f"unknown tool: {name}")

    if not 200 <= status < 300:
        return _error(status, body)
    return body
