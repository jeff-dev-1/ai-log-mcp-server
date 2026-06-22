# ai-log-mcp-server

把「AI 日志分析平台」的 REST 能力封装成 MCP tools，供 Claude Desktop / Cursor 等 MCP 客户端调用。

- 语言：Python 3.10+ · MCP：官方 `mcp` SDK · 传输：stdio · HTTP：`httpx`
- 设计原则：所有 tool 只转调平台 REST，不重写平台逻辑；schema 以平台 `/openapi.json` 为唯一来源。
- 详见 `CLAUDE.md`（工程契约）、`DESIGN.md`（工具设计）、`WORKFLOW.md`（阶段协议）。

## 环境变量

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `APP_BASE_URL` | 平台 REST 基址 | `http://192.168.88.210:8000` |

> backend REST 是开放的（登录门只在前端），无需鉴权 token。

## 本地运行

```bash
# 1. 安装（含测试依赖用 .[dev]）
pip install -e .

# 2. 指定平台地址（不指定则用默认 demo 地址）
export APP_BASE_URL="http://192.168.88.210:8000"

# 3. 以 stdio 方式启动 MCP server
python -m ai_log_mcp.server
```

> 调试推荐用 MCP Inspector：`npx @modelcontextprotocol/inspector python -m ai_log_mcp.server`
> 连通自检：`python -m ai_log_mcp.check`（拉到 `${APP_BASE_URL}/openapi.json` 即通）

## 可用工具（本轮 MVP）

所有 tool 的入参/出参 schema 以 `${APP_BASE_URL}/openapi.json` 为唯一来源（见 `DESIGN.md` §3.1），只转调 REST、原样透传响应；非 2xx 返回 `{error, status, body}`。

| tool | 端点 | 入参 | 说明 |
| --- | --- | --- | --- |
| `list_logs` | `GET /logs` | `limit`（可选, int） | 列最近日志/任务 |
| `get_job` | `GET /logs/jobs/{job_id}` | `job_id`（必填, str） | 取某任务明细/结果 |
| `chat_query` | `POST /chat/query` | `question`（必填）；`log_id`/`top_k`/`backend`/`scenario`（可选） | 对日志做 AI 问答/分析 |
| `health` | `GET /health` | 无 | 平台健康/连通 |

### 网关安全（只读，面向安全工程师）

均为无入参 GET；openapi 无输出 schema，下表「返回内容」即选 tool 依据（见 `DESIGN.md` §3.2）。

| tool | 端点 | 返回内容 |
| --- | --- | --- |
| `gateway_observability` | `GET /gateway/observability` | 网关指标：调用/失败/拦截数、错误率、token 用量与成本、p50/p95 延迟、分布 |
| `gateway_info` | `GET /gateway/info` | 网关配置：网关名、provider、默认后端、后端列表与路由、guardrails |
| `gateway_prompts` | `GET /gateway/prompts` | 网关提示词：system_prompts 与 scenario_prompts |
| `gateway_redteam_report` | `GET /gateway/redteam-report` | 红队报告：通过率、各类别（注入/越狱/PII…）通过情况与失败用例 |
| `gateway_supply_chain_report` | `GET /gateway/supply-chain-report` | 供应链报告：放行/拦截/待审批计数与各依赖判定 |
| `gateway_pentest_report` | `GET /gateway/pentest-report` | 渗透报告：目标、gate 结论、高/中危数量与 findings |
| `gateway_supply_chain_samples` | `GET /gateway/supply-chain/samples` | 供应链可选样本：启用状态、支持市场、示例样本 |

### 上传（写操作）

| tool | 端点 | 入参 | 说明 |
| --- | --- | --- | --- |
| `upload_logs` | `POST /logs/upload`（multipart） | `file_path?` / `content?`（互斥，二选一）；`filename?`；`source?`（`nginx`/`app`/`custom`） | 上传日志文件做分析，返回 `UploadResponse` |

> `file_path` 首选（本地路径，server 读盘上传）；`content` 兜底（内联文本，不依赖文件系统）。大小上限默认 5 MB，可经 `UPLOAD_MAX_BYTES` 调整。详见 `DESIGN.md` §6。

### 网关动作（写/查询）

| tool | 端点 | 入参 | 说明 |
| --- | --- | --- | --- |
| `gateway_guardrail_test` | `POST /gateway/guardrail-test` | `text` | 送文本，得护栏裁定（verdict/matched_rules） |
| `gateway_supply_chain_check` | `POST /gateway/supply-chain-check` | `marketplace`, `item_id`, `version?` | 送依赖标识，得供应链判定（state/risk/findings） |

> 语义为裁定/查询，不写业务数据（仅令 gateway observability 计数+1）。
> 3 个 `*-report` 的 **POST**（写回扫描报告）为 **CI-only，不暴露为 tool**——读取用对应 GET（见 `DESIGN.md` §5）。

## 在 Claude Desktop 注册

编辑 `claude_desktop_config.json`（macOS：`~/Library/Application Support/Claude/claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "ai-log": {
      "command": "python",
      "args": ["-m", "ai_log_mcp.server"],
      "env": {
        "APP_BASE_URL": "http://192.168.88.210:8000"
      }
    }
  }
}
```

重启 Claude Desktop 后，工具会出现在工具列表中。

## 在 Cursor 注册

编辑 `~/.cursor/mcp.json`（或项目级 `.cursor/mcp.json`）：

```json
{
  "mcpServers": {
    "ai-log": {
      "command": "python",
      "args": ["-m", "ai_log_mcp.server"],
      "env": {
        "APP_BASE_URL": "http://192.168.88.210:8000"
      }
    }
  }
}
```

## 如何验收

```bash
# 1. 单元测试（mock REST，不依赖平台在线）
pip install -e '.[dev]'
python -m pytest -q                       # 期望: 41 passed, 2 deselected

# 2. 集成测试（需可达 ${APP_BASE_URL}）。⚠️ 含真上传，有副作用：会在平台创建真任务、污染数据
python -m pytest -m integration -q        # 期望: 2 passed（连通性 + 真上传）
#   只跑连通性、不触发上传：pytest -m integration -k "not upload"

# 3. stdio 协议级冒烟（真实 MCP client over stdio 驱动本 server）
python scripts/smoke_stdio.py             # 期望: 列出 14 个 tool + health 返回, SMOKE OK
```

完整逐条验收（PRD §4 A1–A7）记录见 `WORKFLOW.md` 阶段 3。

## 参考链接

- demo UI：http://192.168.88.210:3000/ （登录 `admin` / `vibecoding2026`，仅前端）
- REST 文档（人读）：http://192.168.88.210:8000/docs
- 机读契约（唯一权威）：http://192.168.88.210:8000/openapi.json
