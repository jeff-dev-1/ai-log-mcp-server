# 从 0 跟做：ai-log-mcp-server 构建手册

> 给学生的「从零复现」手册。**仅文档**，不改代码。
> 配合 git tag `step-0` … `step-6c` 使用：每一步都有一个可检出的提交。

---

## 1. 总览

### 这是什么
一个 **MCP server**：把「AI 日志分析平台」已有的 REST 能力，封装成一组 MCP tools，供 Claude Desktop / Cursor 等 MCP 客户端通过自然语言调用。它**不是**新平台——只做「组装请求 → 调平台 REST → 透传响应」。

### 最终成果
- **14 个 tool**，覆盖平台 17 个 REST 操作中的 14 个。
- **3 个操作显式排除**（CI-only，写明理由）。
- 测试：`pytest -q` → 41 passed, 2 deselected；stdio 冒烟 → 14 tools, SMOKE OK。
- 全程 **17 个提交 + 18 个 tag**（`step-5a` 是补打的注解 tag，与 `step-5c` 同指一个提交），每步可追溯。

### 技术栈（钉死，引 `CLAUDE.md` §2）
| 项 | 选定 |
| --- | --- |
| 语言 | Python 3.10+ |
| MCP | 官方 `mcp` SDK |
| 传输 | stdio（唯一） |
| HTTP | `httpx` |
| 鉴权 | 无（backend REST 开放，登录门只在前端） |

### 贯穿全程的四条红线（引 `CLAUDE.md` §4）
1. schema 唯一源是运行实例的 `/openapi.json`，不手抄、不臆造。
2. 只转调 REST，不重写平台逻辑。
3. 不硬编码 base URL，走 `APP_BASE_URL`。
4. 不加鉴权、只用 stdio。

### 分层文档（Context Stack）
- **L1 `CLAUDE.md`**：工程契约（技术栈/红线/目录）。
- **L2 `DESIGN.md`**：tool ↔ REST 端点映射。
- **L3 `WORKFLOW.md`**：阶段协议（阶段 1 契约同步 → 2 实现 → 3 验收）+ 各批验收记录。
- `docs/PRD.md`：产品需求。`README.md`：怎么跑/怎么注册。

---

## 2. 逐步轨迹（step-0 → step-6c）

> 每节：**真实提示词（逐字，可直接复制）** → 关键决策/教学点 → 验收 → 对应 tag。
> 大的"批次"内部用 `a/b/c` 子步：通常 `a`=阶段1填表、中间=实现、末步=阶段3收口。
> ⚠️ 下面的提示词是当时**原样使用**的——红线约束、`⚠️` 副作用提醒、"先给计划我确认"的 gating 一字未删。
> 照抄即可复现同样的轨迹；删掉这些约束，复现质量会下降。

### step-0 — Context Stack 契约
- **真实提示词（逐字）**：
```
你是架构助手。我要基于一个"AI 日志分析应用"写一个 MCP server。

要求：先不要输出任何代码，只输出计划（要建哪些文件、每个文件写什么）；我确认后你再生成；最后告诉我怎么验收。

要建的文件（对应 Context Stack 分层）：
a. CLAUDE.md — L1 工程契约（项目身份、技术栈不要换、目录约定、禁止事项、必须执行）
b. DESIGN.md — L2 设计（暴露哪些 MCP tool，各自包哪个 REST 端点，入参/出参）
c. WORKFLOW.md — L3 阶段协议
d. README.md — 给人看：怎么跑、怎么在 Claude/Cursor 里注册

技术栈（请在 CLAUDE.md 钉死）：Python，官方 mcp SDK，stdio 传输。

关键约束：
- 工具的入参/出参 schema 以运行实例的 /openapi.json 为唯一来源，不要手抄、不要臆造。
- 一律通过 REST 调用平台，不重写平台逻辑。
- backend REST 是开放的（登录门只在前端），MCP 直接调 :8000，无需鉴权 token。
- 平台 base URL 走环境变量 APP_BASE_URL，默认下面的 demo 地址，不硬编码。

环境信息：
- demo 界面：<平台 UI 地址> （登录 admin / <由讲师提供>，仅前端）
- REST API 文档：<平台>/docs
- 机读契约：<平台>/openapi.json
```
- **教学点**：先立**契约**再写任何代码。L1 钉死不可变项，下层服从上层。此时 DESIGN 映射表是空的 `_TBD_` 骨架——**故意的**，留给阶段 1 用真实 openapi 填。
- **验收**：4 文件齐、红线可读、层级声明服从。
- **tag**：`step-0`

### step-1 — PRD
- **真实提示词（逐字）**：
```
基于 CLAUDE.md，你现在是产品与架构助手。请不要写代码。

先输出计划，再生成 docs/PRD.md，内容包含：
1. 目标用户与核心场景（SRE / 应用工程师 / 安全工程师）
2. MVP 功能边界（明确 in scope / out of scope）。用能力描述，具体端点清单以 WORKFLOW 阶段 1 拉取的 /openapi.json 为准，本文件不列举/不臆造端点。
3. 产品级数据流（用户 → 能力 → 结果）。技术性的 tool↔REST 端点映射属于 DESIGN.md，本文件只引用、不重画。
4. 验收标准（每条可观察、可验证，禁用"流畅"等主观词）。
5. 风险与待确认问题。

另外：把 docs/PRD.md 补进 CLAUDE.md 第 3 节目录约定，保持 L1 自洽。
```
- **教学点**：PRD 写**能力**不写端点——端点是 L2 的事，避免跨层重复与臆造。验收标准必须二元可判定，禁"流畅"等主观词。
- **验收**：A1–A7 每条可执行；PRD 不含端点清单。
- **tag**：`step-1`

### step-2 — 项目骨架
- **真实提示词（逐字）**：
```
基于 docs/PRD.md、DESIGN.md 和 CLAUDE.md 的目录约定，生成项目骨架（仅结构，不含具体业务 tool）。

先列完整目录树让我确认，再生成关键文件，最后给可执行的验收命令。

骨架范围（务必遵守）：
- 只产：目录结构、pyproject.toml、.env.example（APP_BASE_URL 默认 <平台地址>）、MCP server 启动入口（stdio 传输、httpx 客户端、读 APP_BASE_URL、一个空的 tool 注册位）。
- 不要生成任何具体 tool（不按 PRD 的 C1–C5 建 tool 文件）。tool↔端点映射当前为 _TBD_，其填充是 WORKFLOW.md 阶段 1 的第一步，早于任何 tool 代码。
- 可加一个连通性自检（能拉到 ${APP_BASE_URL}/openapi.json 即通），为阶段 1 铺路。

验收命令需可实际运行：装包、stdio 启动不报错、连通 openapi、tools/list 返回（空列表也算通过）。
```
- **教学点**：骨架先于 tool。`config.get_base_url()` 单点读环境变量（红线 3 的落地）。`list_tools()` 返回 `[]` 且注释"待阶段 1 填"——**不臆造 schema**（红线 1）。
- **验收**：`pip install -e .` 通过；`python -m ai_log_mcp.check` 连通；stdio `tools/list` 返回 `[]`。
- **tag**：`step-2`

### step-3a..3d — 实现核心 tool（一条提示词驱动整批）
- **真实提示词（逐字）**：这一条同时驱动了 step-3a（填表）→3b（测试脚手架）→3c（只读 tool）→3d（chat_query）。助手先给分步实现计划、每步一 commit + 跑测试。
```
基于已填充的 DESIGN.md 映射表实现核心 tool（服从 CLAUDE.md 红线）。

先给实现计划（分几步，每步一个 commit，对应 DESIGN 表里哪几个 tool），我确认后再逐步改，每步跑测试。

约束：
- 每个 tool 的入参/出参 schema 现查 ${APP_BASE_URL}/openapi.json，不照 PRD 臆造；每个 tool 可追溯到 DESIGN 表的一行。
- tool 只做「组装请求 → rest_client 调 REST → 透传响应」；非 2xx 按 DESIGN §4 返回结构化错误。
- 第一步先搭测试脚手架（pytest），并采用 mock REST 层的单测（不依赖 210 在线）；另留一个可选的 @integration 连通性测试。
- 不暴露 DESIGN §5 / PRD Out-of-Scope 标注的端点。
```
> 注：DESIGN 映射表此时尚是 `_TBD_`；助手把"执行 WORKFLOW 阶段 1 填表"作为本批第一步（step-3a），再进 3b/3c/3d。
- **教学点**：**这是「schema 唯一源是 openapi」的第一次实操**。先有契约表，才允许写 tool 代码（WORKFLOW 顺序不可颠倒）。表里只填**引用位置**（如 `#/components/schemas/ChatRequest`），不复制字段。
- **验收**：映射表无 `_TBD_`，每行可在 openapi 定位。
- **tag**：`step-3a`

### step-3b — 测试脚手架
- **提示词**：同 step-3a..3d 那一条（本子步是其"第一步先搭测试脚手架"）。
- **教学点**：单测必须**离线可跑**——mock 掉 `rest_client.make_client`。真实网络的测试用 marker 隔离、默认 deselect（`addopts = -m 'not integration'`）。
- **验收**：`pytest -q` → 5 passed, 1 deselected；`pytest -m integration` → 1 passed。
- **tag**：`step-3b`

### step-3c — 核心只读 tool
- **提示词**：同 step-3a..3d 那一条（实现 `list_logs`/`get_job`/`health` 子步）。
- **教学点**：tool = 组装→`rest_client`→透传。新增 `rest_client.request_json()`：**不抛非 2xx**，把 `{error,status,body}` 的判断交给 tool（§4）。
- **验收**：12 passed；实跑 `get_job` 非法 id → `{error,status:422,body}`。
- **tag**：`step-3c`

### step-3d — AI 分析 tool
- **提示词**：同 step-3a..3d 那一条（实现 `chat_query` 子步）。
- **教学点**：可选字段缺省**交平台**，不在本地臆造默认值（platform 默认 `top_k=5`/`backend=deepseek`）。这是"不重写平台逻辑"的细节落地。
- **验收**：16 passed；实跑返回平台真实 `ChatResponse`。
- **tag**：`step-3d`

### step-3e — 阶段 3：MVP 验收收口
- **真实提示词（逐字）**：
```
执行 WORKFLOW.md 阶段 3：验收。先不扩新端点，把本轮 MVP 收口。请先给验收计划，我确认后再做。

1. stdio 协议级冒烟：写一个最小 MCP 客户端脚本（用官方 mcp SDK 的 client over stdio），对本 server 跑完整握手：initialize → tools/list（应列出 4 个 tool）→ 实际 call 一个 tool（如 health 或 list_logs），打印结果。证明它作为真实 MCP server 在传输层可用，而非只是直调 tools.call()。
2. README 收口：补本轮 4 个 tool 的用法；给出 Claude Desktop / Cursor 的注册 JSON（command/args/env=APP_BASE_URL）；加"如何验收"一节（上面的冒烟脚本 + pytest 命令）。
3. 验收清单：对照 docs/PRD.md §4 的 A1–A7 逐条标注是否满足、用什么命令验证。

约束：不实现 upload/gateway（仍属后续批次）；不改已冻结的 tool 行为。完成后给 commit message。
```
- **紧接一条收尾提示词（逐字）**：
```
先把 scripts/（含 smoke_stdio.py）补进 CLAUDE.md §3 目录约定，把 CLAUDE.md 一并纳入本提交，再提交并打 step-3e。
```
- **教学点**：冒烟用真实 MCP **client** 驱动 server，证明**传输层**可用（而非只直调 `tools.call()`）。验收清单逐条带命令/证据。
- **验收**：16 passed；smoke → 4 tools, SMOKE OK；A1–A7 全绿。
- **tag**：`step-3e`

### step-4a..4d — 批次：gateway 只读（面向安全工程师）
- **真实提示词（逐字）**：
```
开新批次：gateway 只读端点（面向安全工程师视角）。严格按 WORKFLOW.md 阶段 1→3，先给计划我确认。

- 阶段 1：现查 ${APP_BASE_URL}/openapi.json，把 DESIGN §3.2 里 gateway 的只读 GET 端点（observability/info/prompts/各 report GET/supply-chain samples）填进 §3 映射表，标注归属"网关安全·只读"。本批不含 gateway 写操作（guardrail-test/supply-chain-check/提交 report）与 upload。
- 阶段 2：按表逐个实现 tool（每步一 commit + mock 单测），复用既有"组装→rest_client→透传"模式与 DESIGN §4 结构化错误；schema 现查 openapi、可追溯到表的一行。
- 阶段 3：扩冒烟（tools/list 数量更新断言）+ README 工具表 + WORKFLOW 追加本批 A 表验收。
- 约束：不改已冻结的 4 个核心 tool；新增目录/文件回写 CLAUDE.md §3。
- 每步给 commit message（建议 step-4a.. 系列）。

upload_logs 等这批完了，单独用一条"先在 DESIGN 讨论 multipart 方案"的提示词起头，别混进来。
```
- **批内追加的一条（逐字）**——强调 description 的重要性：
```
每个 gateway tool 写清晰的一句话 description：说明该端点返回什么内容/什么报告（因 openapi 无输出 schema，description 是调用方选 tool 的唯一依据）；输出按现有模式原样透传。
```
- **教学点**：
  - 7 个都是**无参 GET** → 用**表驱动**（`GATEWAY_READS = {name: (path, desc)}`）批量注册，避免重复代码，且**不碰已冻结的 4 个核心 tool**。
  - openapi 对这些端点**无输出 schema** → `description` 成为调用方选 tool 的**唯一依据**，因此实地拉一遍真实响应来写准描述（不靠猜）。
- **验收**：26 passed；smoke → 11 tools；WORKFLOW G1–G6 全绿。7 端点实跑返回真实字段。
- **tag**：`step-4a` `step-4b` `step-4c` `step-4d`

### step-5a — DESIGN §6：multipart 上传**方案讨论**（先设计后实现）
- **真实提示词（逐字）**：
```
开始处理 upload_logs（POST /logs/upload，multipart）——先只做设计讨论，不写任何代码、不加 tool。

在 DESIGN.md 新增一节（如 §6「multipart 上传方案」），论证 MCP tool 如何承接文件上传：
1. 列候选入参方案及取舍：
  - A. file_path：tool 收本地路径，server 读文件再 multipart 上传（贴合本地 stdio；但需读任意路径，有安全/可达性问题）。
  - B. content(+filename)：日志内容内联（不依赖文件系统；但大文件撑爆 MCP 参数/上下文）。
  - C. 两者都支持。
2. 结合本 server 运行形态（stdio、可能在用户机或远端）给出推荐方案 + 理由，并明确边界（大小上限、是否限制路径、错误处理）。
3. 现查 ${APP_BASE_URL}/openapi.json，确认 /logs/upload 真实的 multipart 字段名（file 字段名、有无其它 form 字段），写进设计，不臆造。
4. 更新 §3.3 推迟表标注（仍不实现，只是定方案）。

仅文档。完成后告诉我怎么验收这份设计，并给 commit message（建议 step-5a）。
```
- **教学点（重要）**：**为什么 upload 先做设计再实现？** 因为它和前面的 tool 不同——MCP 入参是 JSON、没有原生文件类型，"怎么把文件塞进 JSON 参数"是个**有取舍的设计问题**（本地路径有安全/可达性问题；内联内容会撑爆上下文）。这类决策应先在 L2 落档、达成一致，再写代码。
  - 现查确认：`/logs/upload` 的 multipart 字段就是 `file`(binary) + `source`(enum)，**不臆造**。
- **轨迹注记**：此设计当时未单独提交即转入实现，§6 内容被一并提交进 `step-5c`；后补了**注解 tag `step-5a` 指向 step-5c 提交**作为锚点（不重写历史）。这是个真实的工程教训：**确认每步落盘，轨迹才不断**。
- **tag**：`step-5a`（注解，指向 `step-5c` 提交）

### step-5b..5c — 实现 upload_logs + 收口
- **真实提示词（逐字）**：
```
实现 upload_logs，严格按 DESIGN.md §6 已定方案（C：file_path 首选 / content 兜底，二者互斥）。服从 CLAUDE.md 红线，不改已冻结的 11 个 tool。

- inputSchema 按 §6.5：file_path? / content? / filename? / source?(enum，现查 openapi 确认枚举)；schema 取自 ${APP_BASE_URL}/openapi.json。
- 行为：按方案取字节 → files={"file": (filename, bytes)} + data={"source": source} → POST /logs/upload → 透传 UploadResponse；非 2xx 按 §4 结构化错误。
- tool 侧前置校验（这批的重点，都要单测覆盖）：互斥冲突（都给/都不给）、超大小上限（UPLOAD_MAX_BYTES 默认 5MB）、source 非法枚举、file_path 不存在/非普通文件 → 均返回结构化错误，不抛栈。
- 测试：mock REST 层，覆盖 file_path 成功 / content 成功 / 互斥错误 / 超限 / 枚举非法 / 平台 422 六路；file_path 用例用临时文件。
- 阶段 3 收口：smoke 断言 11→12、README 工具表加 upload、WORKFLOW 追加本批 A 表。DESIGN §3.3 把 upload 移出推迟表。
- 每步给 commit message（建议 step-5b..）。
```
- **同时给出的副作用提醒（逐字，关键）**：
```
⚠️ 一个要提醒它的副作用：真实上传会在平台创建一条真任务、污染数据。所以——单测全程 mock（不打 210）；若想加 @integration 真上传，用极小的一次性测试文件并明确标注它有副作用，别塞进默认跑的用例。
```
- **教学点：tool-side 前置校验 vs 交平台 422 的取舍**。
  - 凡平台**无法表达或表达成本高**的约束，在 tool 侧前置拦截、返回结构化错误且**不触达平台**：互斥（都给/都不给）、超大小上限（`UPLOAD_MAX_BYTES` 默认 5MB）、`source` 非法枚举、`file_path` 不存在/非普通文件。
  - 凡平台**本就会校验**的（如缺必填字段），可以**交平台返回 422**，tool 只按 §4 包装——见 step-6b。
  - 判据：本地能廉价挡掉的脏输入就别浪费一次网络往返；平台才是权威的地方就别在本地复刻它的规则。
- **验收**：36 passed, 2 deselected（含 `@integration` 真上传，**有副作用、默认跳过**）。
- **tag**：`step-5b`

### step-5c — 阶段 3 收口（upload）
- **提示词**：同 step-5b..5c 那一条（其"阶段 3 收口"子步）。
- **教学点**：写操作的真实测试有**副作用**（在平台造真任务/污染数据）→ 必须 `@integration` + 默认跳过 + 一次性极小文件，并在文档里**显式警示**。
- **验收**：smoke → 12 tools；U1–U10 全绿。
- **tag**：`step-5c`

### step-6a..6c — 批次：gateway 写操作（含**范围判断**）
- **真实提示词（逐字）**：
```
开最后一批：gateway 写操作，严格 WORKFLOW.md 阶段 1→3，先给计划我确认。

- 阶段 1（含范围判断）：现查 openapi 的 5 个 POST（guardrail-test/supply-chain-check/redteam-report/supply-chain-report/pentest-report）。逐个评估是否是面向用户的 MCP 能力：
  - guardrail-test、supply-chain-check 是"动作/查询"类（送入参→得裁定），纳入本批；
  - 3 个 *-report 的 POST 是 CI 提交报告用途，建议标 Out-of-Scope（CI-only）并说明理由（GET 已在 gateway 只读批暴露，足够用户读报告）。
把结论写进 DESIGN（纳入的填映射表，排除的写明理由），更新 §3.3。
- 阶段 2：实现纳入的 tool（body schema 现查 openapi、可追溯、§4 错误）；每步 commit + mock 单测。
- 阶段 3：smoke 数量更新断言、README、WORKFLOW A 表。
- 约束：不改已冻结的 12 个 tool；写操作默认不做会改平台状态的 integration 测试（要加须标 @integration 且默认跳过）。
- commit 建议 step-6a..。
```
- **教学点：为什么 3 个 `*-report` 的 POST 被排除（CI-only）？**
  - 它们的 body 是**整份扫描产物**（与各自 GET 响应同形），由 CI/扫描器生成并写回——**不是用户在对话里能提供的入参**。
  - 用户**读取**这些报告的需求，已由 gateway 只读批的对应 **GET** 覆盖，足够。
  - 暴露写回 = 让 MCP 客户端覆盖平台报告状态，超出"日志分析"的用户能力边界。
  - 对比之下，`guardrail-test`(`{text}`) 和 `supply-chain-check`(`{marketplace,item_id,version?}`) 是"送入参→得裁定"的**用户动作**，故纳入。
  - **教学点**：阶段 1 不只是"填表"，还包含**范围判断**——不是每个端点都该变成 tool。排除项要写明理由（DESIGN §5）。
- **验收**：41 passed；smoke → 14 tools；W1–W7 全绿。2 端点实跑：guardrail 对注入文本返回 `BLOCKED`。
- **tag**：`step-6a` `step-6b` `step-6c`

---

## 3. 端点覆盖盘点（17 操作 = 14 tool + 3 排除）

> 平台 `/openapi.json` 有 14 条 path、17 个操作（3 条 path 同时有 GET+POST）。

| # | 操作 | 处置 | tool / 理由 |
| --- | --- | --- | --- |
| 1 | `GET /logs` | ✅ tool | `list_logs` |
| 2 | `GET /logs/jobs/{job_id}` | ✅ tool | `get_job` |
| 3 | `POST /chat/query` | ✅ tool | `chat_query` |
| 4 | `GET /health` | ✅ tool | `health` |
| 5 | `GET /gateway/observability` | ✅ tool | `gateway_observability` |
| 6 | `GET /gateway/info` | ✅ tool | `gateway_info` |
| 7 | `GET /gateway/prompts` | ✅ tool | `gateway_prompts` |
| 8 | `GET /gateway/redteam-report` | ✅ tool | `gateway_redteam_report` |
| 9 | `GET /gateway/supply-chain-report` | ✅ tool | `gateway_supply_chain_report` |
| 10 | `GET /gateway/pentest-report` | ✅ tool | `gateway_pentest_report` |
| 11 | `GET /gateway/supply-chain/samples` | ✅ tool | `gateway_supply_chain_samples` |
| 12 | `POST /logs/upload` | ✅ tool | `upload_logs`（multipart，方案 C） |
| 13 | `POST /gateway/guardrail-test` | ✅ tool | `gateway_guardrail_test` |
| 14 | `POST /gateway/supply-chain-check` | ✅ tool | `gateway_supply_chain_check` |
| 15 | `POST /gateway/redteam-report` | ⛔ 排除 | CI-only：写回扫描产物，非用户入参；读取用 #8 |
| 16 | `POST /gateway/supply-chain-report` | ⛔ 排除 | CI-only：同上；读取用 #9 |
| 17 | `POST /gateway/pentest-report` | ⛔ 排除 | CI-only：同上；读取用 #10 |

合计：**14 暴露 + 3 排除 = 17 操作全部处置，无遗漏、无臆造。**

---

## 4. 学生如何跟做

### 方式 A：对照已完成的仓库（最快）
```bash
git clone <repo> && cd ai-log-mcp-server
git tag                       # 看 step-0 .. step-6c 全序列

# 跳到任意一步的状态，对照当时的产物
git checkout step-2           # 看骨架长什么样
git checkout step-3c          # 看第一个真正的 tool
git checkout step-6c          # 回到最终态（或 git checkout main）

# 看某步具体改了什么
git show step-3d              # chat_query 那次提交的完整 diff
git log --oneline --decorate # tag ↔ commit 全景
```

### 方式 B：在自己的空仓从 0 复现（学得最扎实）
按 §2 每一节的「精炼版提示词」，依次让 AI 助手产出该步，每步做完就：
```bash
git add -A && git commit -m "step-x: ..." && git tag step-x
```
做完一步用对应的「验收命令」自检，再进下一步。**严格遵守 WORKFLOW 阶段顺序**：阶段 1 填表 → 阶段 2 写码 → 阶段 3 验收，不可颠倒。

### 跑起来 / 验收（任意时刻）
```bash
pip install -e '.[dev]'
python -m ai_log_mcp.check          # 连通自检：拉到 /openapi.json 即通
python -m pytest -q                 # 期望 41 passed, 2 deselected
python scripts/smoke_stdio.py       # 期望 14 tools, SMOKE OK
# 集成（⚠️ 含真上传副作用）：pytest -m integration -q
# 只连通性不上传：pytest -m integration -k "not upload"
```
环境变量 `APP_BASE_URL` 指向你自己的平台实例；缺省用 demo 地址（见 `README.md`）。

### 五个值得带走的工程习惯
1. **契约先行**：先 openapi/DESIGN，再代码。schema 永远现查、不臆造。
2. **分层不越界**：PRD 写能力、DESIGN 写映射、代码只转发；各司其职。
3. **测试离线可跑**：mock 外部依赖；有副作用的真测试 marker 隔离、默认跳过。
4. **该挡的在本地挡，该交平台的别复刻**：tool-side 校验 vs 平台 422 的取舍。
5. **每步落盘 + tag**：轨迹断了（如 step-5a）就是真实的教训。

---

> 本手册随项目演进；端点或 tool 变化时，回到 WORKFLOW 阶段 1 重新对照 `/openapi.json`，并更新 §3 盘点表。
