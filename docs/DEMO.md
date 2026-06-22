# 现场演示脚本（3 分钟）

> 目标：现场展示「问一句自然语言 → Claude 自主调本仓工具 → 平台返回真实结果」。
> 本 server 是 stdio，由客户端按需拉起，**无需部署**。注册见 `README.md` / 下方"演示前准备"。

## 演示前准备（务必）

1. **注册**（method A，已做过则跳过）：
   ```bash
   claude mcp add ai-log --env APP_BASE_URL=http://<平台host>:8000 \
     -- "$(pwd)/.venv/bin/python" -m ai_log_mcp.server
   ```
2. **新开一个会话**（在本项目目录）——MCP 在会话启动时加载，旧会话不会动态加载。
3. **预热**：把 Demo 1、Demo 2 各跑一遍（预热连接/平台缓存，临场 4–5s 出结果，避免冷启动）。
4. 打开两样东西备用：`docs/BUILD-FROM-ZERO.md`、`CLAUDE.md`。

## 0:00–0:30 · 立框架

> "这是我从 0 写的一个 MCP server。它给 Claude 加了一项能力——查我们的日志分析平台。我没给它写任何'怎么查'的逻辑，全靠平台的 REST API。看。"

→ 打 `/mcp`，亮出 **ai-log，14 个 tool**。

## 0:30–1:15 · Demo 1（wow：自然语言 → 真实分析）

**问**（带 top_k=20，保证召回稳、答案丰富）：
> 让平台 AI 分析（top_k=20）：最近日志里有哪些错误和攻击行为？

预期：Claude **只调 `chat_query`**（top_k=20），4–6s 返回平台 LLM 的真实分析（Apache `[error]`：扫描/枚举 `File does not exist`、`Directory index forbidden`、URI 过长、读头失败、客户端 IP、时间段）。

> 话术："注意两点——是 Claude 自己决定调哪个工具；答案来自平台的 AI，我的 MCP 只是把问题转过去、把结果透传回来。"

**备选（更自然、不露旋钮）**：`帮我归纳最近日志里的可疑扫描/攻击行为`
——但 ⚠️ 用这句**务必台下先验**它在默认 top_k=5 下也能给出丰富答案（RAG 召回非确定性，见"临场保险"）。

## 1:15–2:00 · Demo 2（广度 + 安全，最有冲击力）

**问**：
> 帮我用 guardrail 测下这句有没有注入：ignore previous instructions

预期：Claude 选 `gateway_guardrail_test` → **BLOCKED** + 命中 `prompt_injection` 规则，秒回。

> 话术："14 个工具，Claude 按需挑。连平台的安全护栏也暴露成了工具——这就是 MCP 的价值：让 AI 自主编排你的能力。"

**加分变体**（证明不是无脑全拦，对比更有说服力）：
> 再用 guardrail 测一句正常的：今天天气不错

预期：**ALLOWED**。

## 2:00–2:45 · 揭底（方法论收益）

切到 repo，开 `docs/BUILD-FROM-ZERO.md`。

> "没有魔法。每个工具一一对应一个 REST 端点，schema 全部来自 `/openapi.json`，一个字段都没手写。整个项目分成带 tag 的若干步——你们可以 `git checkout step-3c`，看我当时怎么一步步长出来的，照着复现。"

**（可选教学点，承接 Demo 1）**：
> "顺带说个细节：同一个问题，top_k 从 5 提到 20，结论会从'看起来没 ERROR'变成'一堆扫描型 error'——因为平台是 RAG 检索式问答，只在召回的片段里判断。这恰恰说明：MCP 只透传，**检索/分析的特性完全是平台的，我没改一行**。"

## 2:45–3:00 · 收口

> "`CLAUDE.md` 这份工程契约从头管到尾：schema 唯一源、只转调不重写、stdio-only。契约 + 工作流，从 0 到 14 个工具全覆盖——这才是今天想让你们带走的。"

---

## 临场保险

- **某句卡住** → Ctrl-C，切 Demo 2（guardrail 永远秒回，最稳，可当主力 wow）。
- **默认 top_k=5 召回不稳** → Demo 1 **务必带 `top_k=20`**（或台下先预热确认丰富答案）。RAG 召回是语义匹配、非确定性：低 top_k 同一句可能这次丰富、下次答"无 ERROR"，台上别赌。
- **别问**"列出所有日志/任务" → 会触发 `list_logs` 拉回完整 job 对象（内嵌原始日志、体积大、慢）。
  - tool 的 description 已标注并引导分析类问题改用 `chat_query`，但口头也别往那引导。
  - `limit` 别用：实测平台对部分 limit 值返回 500，不可靠。
- **备选问法**（都走 chat_query，安全快）：
  - "平台分析下最近的访问异常集中在哪些 IP？"
  - "最近的日志里有没有可疑的扫描/爬虫行为？"

## 一句话原理（被追问时）

MCP server 自身**没有任何业务/分析/规则逻辑**：它把 14 个工具调用各自映射到平台一个 REST 端点，组装请求 → 调 REST → 原样透传响应。分析、护栏裁定、检索全在平台侧。这正是 `CLAUDE.md` 的红线：schema 唯一源 `/openapi.json`、只转调不重写、仅 stdio。
