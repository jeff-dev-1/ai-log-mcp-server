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

## 3. Tool ↔ 端点映射表（骨架，待 openapi 填充）

| MCP tool | HTTP 方法 + 路径 | 入参来源（openapi） | 出参 | 类型 | 说明 |
| --- | --- | --- | --- | --- | --- |
| _TBD_ | `GET /...` | `paths./....parameters` | `...responses.200` | 只读 | 待填充 |
| _TBD_ | `GET /.../{id}` | path 参数 | `...responses.200` | 只读 | 待填充 |
| _TBD_ | `POST /...` | `requestBody` | `...responses.200` | 写操作 | 待填充 |

> 填充规则：遍历 openapi 的 `paths`，对每个 `(path, method)` 生成一行；入参/出参列只填**引用位置**（如 `paths./logs.get.parameters`），不复制字段内容。

## 4. 通用约定

- **base URL**：所有 tool 的请求基址 = `APP_BASE_URL`（默认 `http://192.168.88.210:8000`）。
- **鉴权**：无。不带 token、不做登录（backend REST 开放）。
- **错误处理**：REST 返回非 2xx 时，tool 返回结构化错误（含 status code + 响应体），不吞错、不重试登录。
- **超时**：统一设置 httpx 超时（具体值在实现阶段定，记入代码注释）。

## 5. 不在范围内（Out of Scope）

- 不暴露前端专用 / 登录相关端点（若 openapi 中存在）。
- 不做分页聚合、缓存、字段裁剪等「平台逻辑」——交给调用方或平台。
