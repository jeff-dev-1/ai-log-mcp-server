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

> 每节：精炼版提示词 → 关键决策/教学点 → 验收 → 对应 tag。
> 大的"批次"内部用 `a/b/c` 子步：通常 `a`=阶段1填表、中间=实现、末步=阶段3收口。

### step-0 — Context Stack 契约
- **提示词**：写 4 个契约文档（CLAUDE/DESIGN/WORKFLOW/README），先出计划、确认后生成。技术栈钉死；schema 唯一源 openapi；只调 REST、不硬编码、无 token。
- **教学点**：先立**契约**再写任何代码。L1 钉死不可变项，下层服从上层。此时 DESIGN 映射表是空的 `_TBD_` 骨架——**故意的**，留给阶段 1 用真实 openapi 填。
- **验收**：4 文件齐、红线可读、层级声明服从。
- **tag**：`step-0`

### step-1 — PRD
- **提示词**：生成 `docs/PRD.md`（目标用户 SRE/应用/安全；MVP 边界用能力描述不列端点；数据流引用 DESIGN 不重画；验收 A1–A7 可观察；风险）。登记进 CLAUDE §3。
- **教学点**：PRD 写**能力**不写端点——端点是 L2 的事，避免跨层重复与臆造。验收标准必须二元可判定，禁"流畅"等主观词。
- **验收**：A1–A7 每条可执行；PRD 不含端点清单。
- **tag**：`step-1`

### step-2 — 项目骨架
- **提示词**：只产结构 + `pyproject.toml` + `.env.example`（`APP_BASE_URL` 默认 demo）+ stdio server 入口（空 tool 注册位）+ 连通自检；**不产任何具体 tool**。
- **教学点**：骨架先于 tool。`config.get_base_url()` 单点读环境变量（红线 3 的落地）。`list_tools()` 返回 `[]` 且注释"待阶段 1 填"——**不臆造 schema**（红线 1）。
- **验收**：`pip install -e .` 通过；`python -m ai_log_mcp.check` 连通；stdio `tools/list` 返回 `[]`。
- **tag**：`step-2`

### step-3a — 阶段 1：填 DESIGN 映射表（核心日志）
- **提示词**：现查 `/openapi.json`，把核心日志端点填进 DESIGN §3，标命名与引用位置。
- **教学点**：**这是「schema 唯一源是 openapi」的第一次实操**。先有契约表，才允许写 tool 代码（WORKFLOW 顺序不可颠倒）。表里只填**引用位置**（如 `#/components/schemas/ChatRequest`），不复制字段。
- **验收**：映射表无 `_TBD_`，每行可在 openapi 定位。
- **tag**：`step-3a`

### step-3b — 测试脚手架
- **提示词**：pytest + **mock REST 层**（httpx `MockTransport`，不依赖平台在线）+ 一个 `@integration` 连通性测试（默认跳过）。
- **教学点**：单测必须**离线可跑**——mock 掉 `rest_client.make_client`。真实网络的测试用 marker 隔离、默认 deselect（`addopts = -m 'not integration'`）。
- **验收**：`pytest -q` → 5 passed, 1 deselected；`pytest -m integration` → 1 passed。
- **tag**：`step-3b`

### step-3c — 核心只读 tool
- **提示词**：实现 `list_logs` / `get_job` / `health`；非 2xx 按 DESIGN §4 返回结构化错误。
- **教学点**：tool = 组装→`rest_client`→透传。新增 `rest_client.request_json()`：**不抛非 2xx**，把 `{error,status,body}` 的判断交给 tool（§4）。
- **验收**：12 passed；实跑 `get_job` 非法 id → `{error,status:422,body}`。
- **tag**：`step-3c`

### step-3d — AI 分析 tool
- **提示词**：实现 `chat_query`（POST /chat/query），inputSchema 引 `ChatRequest`，**只透传已提供字段**。
- **教学点**：可选字段缺省**交平台**，不在本地臆造默认值（platform 默认 `top_k=5`/`backend=deepseek`）。这是"不重写平台逻辑"的细节落地。
- **验收**：16 passed；实跑返回平台真实 `ChatResponse`。
- **tag**：`step-3d`

### step-3e — 阶段 3：MVP 验收收口
- **提示词**：写 stdio **协议级冒烟**（官方 mcp client over stdio）；README 补工具表 + 注册 JSON + 「如何验收」；WORKFLOW 记 A1–A7。
- **教学点**：冒烟用真实 MCP **client** 驱动 server，证明**传输层**可用（而非只直调 `tools.call()`）。验收清单逐条带命令/证据。
- **验收**：16 passed；smoke → 4 tools, SMOKE OK；A1–A7 全绿。
- **tag**：`step-3e`

### step-4a..4d — 批次：gateway 只读（面向安全工程师）
- **提示词**：现查 7 个 gateway GET 端点填表（4a）；实现状态/配置 3 个（4b）、安全报告 4 个（4c）；阶段 3 冒烟断言 4→11（4d）。
- **教学点**：
  - 7 个都是**无参 GET** → 用**表驱动**（`GATEWAY_READS = {name: (path, desc)}`）批量注册，避免重复代码，且**不碰已冻结的 4 个核心 tool**。
  - openapi 对这些端点**无输出 schema** → `description` 成为调用方选 tool 的**唯一依据**，因此实地拉一遍真实响应来写准描述（不靠猜）。
- **验收**：26 passed；smoke → 11 tools；WORKFLOW G1–G6 全绿。7 端点实跑返回真实字段。
- **tag**：`step-4a` `step-4b` `step-4c` `step-4d`

### step-5a — DESIGN §6：multipart 上传**方案讨论**（先设计后实现）
- **提示词**：只做设计——论证 MCP tool 如何承接文件上传，列候选 A(file_path)/B(content)/C(两者)取舍，结合 stdio 形态给推荐 + 边界；现查 openapi 确认真实 multipart 字段名。
- **教学点（重要）**：**为什么 upload 先做设计再实现？** 因为它和前面的 tool 不同——MCP 入参是 JSON、没有原生文件类型，"怎么把文件塞进 JSON 参数"是个**有取舍的设计问题**（本地路径有安全/可达性问题；内联内容会撑爆上下文）。这类决策应先在 L2 落档、达成一致，再写代码。
  - 现查确认：`/logs/upload` 的 multipart 字段就是 `file`(binary) + `source`(enum)，**不臆造**。
- **轨迹注记**：此设计当时未单独提交即转入实现，§6 内容被一并提交进 `step-5c`；后补了**注解 tag `step-5a` 指向 step-5c 提交**作为锚点（不重写历史）。这是个真实的工程教训：**确认每步落盘，轨迹才不断**。
- **tag**：`step-5a`（注解，指向 `step-5c` 提交）

### step-5b — 实现 upload_logs
- **提示词**：按 §6 方案 C（file_path 首选 / content 兜底，互斥）实现；**前置校验是重点**，全部 mock 单测覆盖。
- **教学点：tool-side 前置校验 vs 交平台 422 的取舍**。
  - 凡平台**无法表达或表达成本高**的约束，在 tool 侧前置拦截、返回结构化错误且**不触达平台**：互斥（都给/都不给）、超大小上限（`UPLOAD_MAX_BYTES` 默认 5MB）、`source` 非法枚举、`file_path` 不存在/非普通文件。
  - 凡平台**本就会校验**的（如缺必填字段），可以**交平台返回 422**，tool 只按 §4 包装——见 step-6b。
  - 判据：本地能廉价挡掉的脏输入就别浪费一次网络往返；平台才是权威的地方就别在本地复刻它的规则。
- **验收**：36 passed, 2 deselected（含 `@integration` 真上传，**有副作用、默认跳过**）。
- **tag**：`step-5b`

### step-5c — 阶段 3 收口（upload）
- **提示词**：冒烟 11→12；README 加 upload；WORKFLOW U1–U10；DESIGN §3.3 把 upload 移出推迟表。
- **教学点**：写操作的真实测试有**副作用**（在平台造真任务/污染数据）→ 必须 `@integration` + 默认跳过 + 一次性极小文件，并在文档里**显式警示**。
- **验收**：smoke → 12 tools；U1–U10 全绿。
- **tag**：`step-5c`

### step-6a..6c — 批次：gateway 写操作（含**范围判断**）
- **提示词**：现查 5 个 gateway POST，逐个判断是否是面向用户的 MCP 能力（6a）；实现纳入的 2 个（6b）；阶段 3 冒烟 12→14（6c）。
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
