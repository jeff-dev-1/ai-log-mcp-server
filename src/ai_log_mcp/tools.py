"""MCP tool 定义与分发。

边界（CLAUDE.md / DESIGN.md §3）：
- 每个 tool 可追溯到 DESIGN §3.1 的一行；inputSchema 取自现查的 openapi。
- tool 只做「组装请求 → rest_client 调 REST → 透传响应」。
- 非 2xx 按 DESIGN §4 返回结构化错误（status + body），不吞错、不重试登录。
"""

import os

import mcp.types as types

from . import config, rest_client

# /logs/upload 的 source 枚举（现查 openapi: Body_upload_logs_upload_post.source）。
UPLOAD_SOURCES = ("nginx", "app", "custom")

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

# ── upload_logs（multipart，DESIGN §6）─────────────────────────────────────────
TOOLS.append(
    types.Tool(
        name="upload_logs",
        description=(
            "上传日志文件做分析（POST /logs/upload，multipart）。"
            "二选一：file_path（本地路径，首选）或 content（内联文本，兜底），二者互斥。"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "本地文件路径（与 content 互斥，首选）"},
                "content": {"type": "string", "description": "日志内容内联文本（与 file_path 互斥，兜底）"},
                "filename": {"type": "string", "description": "上传文件名（仅配合 content；file_path 缺省取其 basename）"},
                "source": {"type": "string", "enum": list(UPLOAD_SOURCES), "description": "日志来源（可选，平台默认 custom）"},
            },
            "required": [],
        },
    )
)

# ── 网关动作（写/查询，DESIGN §3.3b）──────────────────────────────────────────────
TOOLS.append(
    types.Tool(
        name="gateway_guardrail_test",
        description="送一段文本，得 AI 网关护栏（guardrail）裁定（POST /gateway/guardrail-test）。",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "待检测文本（必填，对应 GuardrailTestRequest.text）"},
            },
            "required": ["text"],
        },
    )
)
TOOLS.append(
    types.Tool(
        name="gateway_supply_chain_check",
        description="送依赖标识，得供应链安全判定（POST /gateway/supply-chain-check）。",
        inputSchema={
            "type": "object",
            "properties": {
                "marketplace": {"type": "string", "description": "市场（必填，如 pypi/npm/hugging_face…）"},
                "item_id": {"type": "string", "description": "条目标识（必填，如包名/模型名）"},
                "version": {"type": "string", "maxLength": 60, "description": "版本（可选）"},
            },
            "required": ["marketplace", "item_id"],
        },
    )
)

# 各网关动作 tool 透传给平台的 body 字段（来自对应 openapi schema）。
_SUPPLY_CHAIN_CHECK_FIELDS = ("marketplace", "item_id", "version")


def _error(status: int, body) -> dict:
    """DESIGN §4 结构化错误（平台非 2xx）。"""
    return {"error": True, "status": status, "body": body}


def _validation_error(detail: str) -> dict:
    """tool 侧前置校验失败的结构化错误（不抛栈，DESIGN §6.4）。"""
    return {"error": True, "status": "validation_error", "body": {"detail": detail}}


def _prepare_upload(arguments: dict):
    """校验并组装 (files, data)。失败返回 ({"error":...}, None)；成功返回 (None, (files, data))。"""
    file_path = arguments.get("file_path")
    content = arguments.get("content")
    filename = arguments.get("filename")
    source = arguments.get("source")
    max_bytes = config.get_upload_max_bytes()

    # 互斥：恰好其一。
    if bool(file_path) == bool(content):
        return _validation_error("file_path 与 content 必须二选一（不能同时提供或都不提供）"), None

    # source 枚举校验（仅在提供时；非法则拦截，不透传给平台吃 422）。
    if source is not None and source not in UPLOAD_SOURCES:
        return _validation_error(f"source 非法：{source!r}，允许值 {list(UPLOAD_SOURCES)}"), None

    if file_path:
        if not os.path.exists(file_path):
            return _validation_error(f"file_path 不存在：{file_path}"), None
        if not os.path.isfile(file_path):
            return _validation_error(f"file_path 不是普通文件：{file_path}"), None
        size = os.path.getsize(file_path)
        if size > max_bytes:
            return _validation_error(f"文件超过上限：{size} > {max_bytes} 字节"), None
        with open(file_path, "rb") as f:
            data_bytes = f.read()
        upload_name = filename or os.path.basename(file_path)
    else:
        data_bytes = content.encode("utf-8")
        if len(data_bytes) > max_bytes:
            return _validation_error(f"content 超过上限：{len(data_bytes)} > {max_bytes} 字节（大文件请改用 file_path）"), None
        upload_name = filename or "upload.log"

    files = {"file": (upload_name, data_bytes)}
    form = {"source": source} if source is not None else None
    return None, (files, form)


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
    elif name == "upload_logs":
        err, prepared = _prepare_upload(arguments)
        if err is not None:
            return err  # 前置校验失败：结构化错误，不调平台
        files, form = prepared
        status, body = rest_client.request_multipart("POST", "/logs/upload", files=files, data=form)
    elif name == "gateway_guardrail_test":
        payload = {"text": arguments.get("text")}
        status, body = rest_client.request_json("POST", "/gateway/guardrail-test", json=payload)
    elif name == "gateway_supply_chain_check":
        # 只透传已提供字段；缺必填项交平台返回 422（§4）。
        payload = {k: arguments[k] for k in _SUPPLY_CHAIN_CHECK_FIELDS if arguments.get(k) is not None}
        status, body = rest_client.request_json("POST", "/gateway/supply-chain-check", json=payload)
    else:
        raise ValueError(f"unknown tool: {name}")

    if not 200 <= status < 300:
        return _error(status, body)
    return body
