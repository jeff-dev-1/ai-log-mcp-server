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

### 3.2 网关安全·只读（gateway 只读批次）

> 全部为无入参 GET。openapi 未声明输出 schema，故 `description`（见代码）是调用方选 tool 的唯一依据；
> 出参列「无 schema」表示 openapi 无强类型定义，输出按现有模式原样透传。

| MCP tool | HTTP 方法 + 路径 | 入参 | 出参（openapi） | 类型 | 返回内容 |
| --- | --- | --- | --- | --- | --- |
| `gateway_observability` | `GET /gateway/observability` | 无 | object（无强类型） | 只读 | 网关可观测指标：调用/失败/拦截数、错误率、token 用量与成本、p50/p95 延迟、按模型/后端/提供方分布 |
| `gateway_info` | `GET /gateway/info` | 无 | object（无强类型） | 只读 | 网关配置：网关名、当前 provider、默认后端、后端列表与路由、guardrails 配置 |
| `gateway_prompts` | `GET /gateway/prompts` | 无 | object（无强类型） | 只读 | 网关提示词：system_prompts 与 scenario_prompts |
| `gateway_redteam_report` | `GET /gateway/redteam-report` | 无 | 无 schema | 只读 | 红队测试报告：整体通过率、各类别（注入/越狱/PII…）通过情况与失败用例 |
| `gateway_supply_chain_report` | `GET /gateway/supply-chain-report` | 无 | 无 schema | 只读 | 供应链安全报告：放行/拦截/待审批计数与各依赖判定 |
| `gateway_pentest_report` | `GET /gateway/pentest-report` | 无 | 无 schema | 只读 | 渗透测试报告：目标、gate 结论、高/中危数量与各项 findings |
| `gateway_supply_chain_samples` | `GET /gateway/supply-chain/samples` | 无 | object（无强类型） | 只读 | 供应链检查的可选样本：是否启用、支持的市场（PyPI/npm/HuggingFace…）与示例 |

### 3.3a 上传（写操作，已实现）

| MCP tool | HTTP 方法 + 路径 | 入参（openapi / §6） | 出参（openapi） | 类型 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `upload_logs` | `POST /logs/upload`（multipart） | `Body_upload_logs_upload_post`：`file`(必填) + `source`(enum) → tool 入参 `file_path?`/`content?`(互斥)/`filename?`/`source?` | `#/components/schemas/UploadResponse` | 写 | 上传日志文件做分析（方案见 §6） |

### 3.3b 网关动作（写/查询，已实现）

> 「送入参→得裁定」类用户能力。POST + JSON body；body schema 现查 openapi。

| MCP tool | HTTP 方法 + 路径 | 入参（openapi） | 出参（openapi） | 类型 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `gateway_guardrail_test` | `POST /gateway/guardrail-test` | `#/components/schemas/GuardrailTestRequest`（必填 `text`） | `#/components/schemas/GuardrailTestResponse` | 写形 | 送一段文本，得护栏（guardrail）裁定 |
| `gateway_supply_chain_check` | `POST /gateway/supply-chain-check` | `#/components/schemas/SupplyChainCheckRequest`（必填 `marketplace`/`item_id`；可选 `version`） | `#/components/schemas/SupplyChainVerdict` | 写形 | 送依赖标识，得供应链安全判定 |

> 「写形」：方法为 POST，但语义是裁定/查询，不写业务数据（仅会令 gateway observability 计数+1）。

### 3.3 待后续批次（仍未实现）

| 候选 tool | 端点 | 类型 | 推迟原因 |
| --- | --- | --- | --- |
| —（无） | — | — | gateway 写操作中"动作类"已纳入 §3.3b；剩余 3 个 *-report POST 见 §5（Out of Scope, CI-only） |

> 推迟项不代表 Out of Scope（见 §5）；它们是未来批次，届时回到阶段 1 续填本表。

## 4. 通用约定

- **base URL**：所有 tool 的请求基址 = `APP_BASE_URL`（默认 `http://192.168.88.210:8000`）。
- **鉴权**：无。不带 token、不做登录（backend REST 开放）。
- **错误处理**：REST 返回非 2xx 时，tool 返回结构化错误（含 status code + 响应体），不吞错、不重试登录。
- **超时**：统一设置 httpx 超时（具体值在实现阶段定，记入代码注释）。

## 5. 不在范围内（Out of Scope）

- 不暴露前端专用 / 登录相关端点（若 openapi 中存在）。
- 不做分页聚合、缓存、字段裁剪等「平台逻辑」——交给调用方或平台。
- **3 个 *-report 的 POST**（`POST /gateway/redteam-report` / `supply-chain-report` / `pentest-report`）：**CI-only，不暴露为 tool**。理由：
  - 其 body 是整份扫描产物（与各自 GET 响应同形），由 CI/扫描器生成并写回，**非用户在对话中能提供的入参**；
  - 用户**读取**这些报告的需求已由 gateway 只读批的对应 **GET**（§3.2）覆盖，足够；
  - 暴露写回会让 MCP 客户端覆盖平台报告状态，超出"日志分析"用户能力边界。

## 6. multipart 上传方案（`upload_logs` 设计，暂不实现）

> 仅设计讨论，本节不产代码、不注册 tool。落地见后续单独批次。

### 6.1 真实契约（现查 openapi，不臆造）

`POST /logs/upload`，`requestBody.required = true`，`content-type: multipart/form-data`，
schema `#/components/schemas/Body_upload_logs_upload_post`：

| form 字段 | 类型 | 必填 | 约束/默认 |
| --- | --- | --- | --- |
| `file` | string(binary) | 是 | 上传的日志文件本体 |
| `source` | string(enum) | 否 | 取值 `nginx` / `app` / `custom`，默认 `custom` |

响应：`200 → #/components/schemas/UploadResponse`；`422 → #/components/schemas/HTTPValidationError`。

> 关键事实：multipart 只有 `file` + 可选 `source` 两个字段，**字段名为 `file`**（httpx `files={"file": ...}`），`source` 走普通 form 字段（`data={"source": ...}`）。

### 6.2 候选入参方案与取舍

MCP tool 的入参是 JSON（无原生文件类型），需把「文件」编码进 JSON 参数。三种承接方式：

| 方案 | 入参 | 优点 | 缺点 |
| --- | --- | --- | --- |
| **A. file_path** | `file_path`（本地路径）+ `source?` | 贴合本地 stdio 形态；大文件不进 MCP 上下文，仅在 server 侧读盘后流式上传 | server 需读任意本地路径，有安全面；若 server 在远端则路径不可达 |
| **B. content(+filename)** | `content`（日志文本）+ `filename?` + `source?` | 不依赖文件系统，远端部署同样可用；调用方/模型可直接给文本 | 大文件撑爆 MCP 参数与对话上下文；二进制/超大日志不适用 |
| **C. 两者都支持** | A、B 二选一（互斥） | 兼顾本地与远端两种形态 | 实现/校验更复杂；需明确互斥与优先级；测试面更大 |

### 6.3 推荐方案 + 理由

**推荐 C（A+B 二选一，互斥），但以 A 为首选路径、B 为补充。**

理由（结合本 server 运行形态）：
- 本 server 是 **stdio**，绝大多数场景与用户在**同一台机器**（Claude Desktop / Cursor 本地拉起）→ A（`file_path`）最自然，且不把日志塞进上下文。
- 但 server 也**可能部署在远端**（A 的路径不可达）→ 保留 B（`content`）作为不依赖文件系统的兜底。
- 二者**互斥**：同次调用只接受其一；都给或都不给 → 报参数错误（不猜测）。

### 6.4 边界（落地时必须遵守）

- **大小上限**：tool 侧设上限（建议默认 **5 MB**，可经环境变量如 `UPLOAD_MAX_BYTES` 调整）。
  - A：读盘前先 `stat` 校验大小，超限直接拒绝，不读入内存。
  - B：对 `content` 字节数做同样上限；提示大文件改用 A。
- **路径限制（方案 A）**：
  - 仅接受**普通文件**（拒绝目录/符号链接指向的特殊文件）；
  - 可选地限制在某允许根目录内（如 `UPLOAD_ALLOWED_ROOT`），默认不开启则记录"读任意路径"为已知风险；
  - 文件不存在/不可读 → 结构化错误，不抛栈。
- **字段映射**：`file` 走 httpx `files=`；`source` 仅允许枚举 `nginx/app/custom`，非法值在 tool 侧拦截（对齐 openapi enum），不透传给平台再吃 422。
- **错误处理**：沿用 DESIGN §4——平台非 2xx 返回 `{error, status, body}`；tool 侧前置校验失败（互斥冲突/超限/路径非法/枚举非法）同样返回结构化错误，不静默。
- **不做的事**：不解析/不改写日志内容、不分片续传、不重试（与 §1「只转调、不重写平台逻辑」一致）。

### 6.5 拟定 tool 形态（仅设计，供落地参考）

- 名称：`upload_logs`，类型：写操作。
- inputSchema（落地时以 openapi enum 为准）：
  - `file_path?: string`、`content?: string`、`filename?: string`、`source?: enum(nginx|app|custom, 默认 custom)`
  - 约束：`file_path` 与 `content` 互斥且至少其一；`filename` 仅配合 `content` 使用。
- 行为：按方案读取字节 → `files={"file": (filename, bytes)}` + `data={"source": source}` → `POST /logs/upload` → 透传 `UploadResponse`。
