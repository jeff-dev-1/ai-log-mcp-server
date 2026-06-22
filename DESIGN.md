# DESIGN.md — L2 设计

> 服从 `CLAUDE.md`（L1）。本文件定义「暴露哪些 MCP tool、各自包哪个 REST 端点、入参/出参」。

## 1. 数据来源声明（唯一权威）

本文件所有 tool 的 **input/output schema 不在此处定义其字段细节**，唯一权威来源是运行实例的：

```
${APP_BASE_URL}/openapi.json
```

- 不手抄、不臆造字段名/类型/必填性。
- 字段细节以拉取到的 openapi 为准；本文件只记录「tool ↔ 端点」的映射关系与命名约定。
- 当 openapi 与本文件冲突时，**openapi 为准**，并按 `WORKFLOW.md` 流程回写更新本文件。

> ⚠️ 当前为**骨架版**：下方映射表尚未用真实 openapi 填充。填充动作是 `WORKFLOW.md` 阶段 1 的第一步。

## 2. 命名与映射原则

- **一个 REST 端点 → 一个 MCP tool**，不合并、不拆分。
- tool 命名 = 动作 + 资源，小写下划线，例如：
  - `GET /logs` → `list_logs`
  - `GET /logs/{id}` → `get_log`
  - `POST /logs/search` → `search_logs`
  - `POST /analyze` → `analyze_logs`
- tool 的 inputSchema 直接取自该端点的 path/query/body 参数（来自 openapi）。
- tool 的输出 = REST 响应原样透传（不二次加工）。
- 只读端点优先暴露；写操作端点需在表中标注「写操作」。

## 3. Tool ↔ 端点映射表

> 阶段 1 已执行：依据现查 `${APP_BASE_URL}/openapi.json`（共 14 端点）填充。
> 入参/出参列只填 openapi 中的**引用位置**，不复制字段内容。

### 3.1 本轮已实现（核心日志）

| MCP tool | HTTP 方法 + 路径 | 入参来源（openapi） | 出参（openapi） | 类型 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `list_logs` | `GET /logs` | `paths./logs.get.parameters`（query `limit`，可选） | `...responses.200`（array） | 只读 | 列最近日志/任务 |
| `get_job` | `GET /logs/jobs/{job_id}` | `paths./logs/jobs/{job_id}.get.parameters`（path `job_id`，必填） | `#/components/schemas/JobResponse` | 只读 | 取某任务明细/结果 |
| `chat_query` | `POST /chat/query` | `#/components/schemas/ChatRequest`（必填 `question`；可选 `log_id/top_k/backend/scenario`） | `#/components/schemas/ChatResponse` | 写形* | 对日志做 AI 问答/分析 |
| `health` | `GET /health` | 无 | `#/components/schemas/HealthResponse` | 只读 | 平台健康/连通 |

> \* `chat_query` 语义为查询，但 HTTP 方法为 POST+body，无副作用；标「写形」以示其方法。

### 3.2 待后续批次（本轮不实现）

| 候选 tool | 端点 | 类型 | 推迟原因 |
| --- | --- | --- | --- |
| `upload_logs` | `POST /logs/upload` | 写 | multipart 文件上传，参数传递特殊，单独成批 |
| `gateway_*`（observability/info/prompts/各 report GET+POST/guardrail-test/supply-chain-check/samples 共 9 端点） | `GET,POST /gateway/*` | 读+写 | 独立「AI 网关安全」域，与核心日志解耦，单独成批 |

> 推迟项不代表 Out of Scope（见 §5）；它们是未来批次，届时回到阶段 1 续填本表。

## 4. 通用约定

- **base URL**：所有 tool 的请求基址 = `APP_BASE_URL`（默认 `http://192.168.88.210:8000`）。
- **鉴权**：无。不带 token、不做登录（backend REST 开放）。
- **错误处理**：REST 返回非 2xx 时，tool 返回结构化错误（含 status code + 响应体），不吞错、不重试登录。
- **超时**：统一设置 httpx 超时（具体值在实现阶段定，记入代码注释）。

## 5. 不在范围内（Out of Scope）

- 不暴露前端专用 / 登录相关端点（若 openapi 中存在）。
- 不做分页聚合、缓存、字段裁剪等「平台逻辑」——交给调用方或平台。
