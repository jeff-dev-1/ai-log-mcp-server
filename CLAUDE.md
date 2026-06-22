# CLAUDE.md — L1 工程契约

> 本文件是项目的最高约束（L1）。L2（`DESIGN.md`）、L3（`WORKFLOW.md`）必须服从本文件。
> 当任何下层文档或代码与本文件冲突时，以本文件为准。

## 1. 项目身份

本项目是一个 **MCP server**，把一个**「AI 日志分析平台」**已有的 REST 能力，封装成一组 MCP tools，供 Claude Desktop / Cursor 等 MCP 客户端调用。

它**不是**新平台、**不是**业务后端、**不是** REST 网关重写。它只是平台 REST API 的一层 MCP 适配壳。

## 2. 技术栈（钉死，不许更换）

| 项 | 选定 | 说明 |
| --- | --- | --- |
| 语言 | **Python 3.10+** | 不引入其他语言 |
| MCP 框架 | **官方 `mcp` SDK** | 不用第三方 MCP 实现 |
| 传输 | **stdio** | 只此一种，不加 HTTP/SSE/WebSocket 传输 |
| HTTP 客户端 | **`httpx`** | 调平台 REST 用 |

> 如需更换上述任一项，必须先改本文件并说明理由，不得在代码里悄悄替换。

## 3. 目录约定

```
ai-log-mcp-server/
├── CLAUDE.md          # L1 工程契约（本文件）
├── DESIGN.md          # L2 设计：MCP tool ↔ REST 端点映射
├── WORKFLOW.md        # L3 阶段协议
├── README.md          # 给人看：怎么跑、怎么注册
├── docs/
│   └── PRD.md         # 产品需求（目标用户/MVP 边界/数据流/验收/风险）
├── scripts/
│   └── smoke_stdio.py # stdio 协议级冒烟（官方 mcp SDK client over stdio）
├── tests/             # pytest 单测（mock REST）+ 可选 @integration
└── src/ai_log_mcp/    # 代码：按 DESIGN §3.1 实现的 tool
```

## 4. 禁止事项（红线）

- ❌ **不手抄、不臆造 schema**。所有 tool 的入参/出参 schema，唯一权威来源是运行实例的 `${APP_BASE_URL}/openapi.json`。
- ❌ **不重写平台业务逻辑**。MCP tool 只做「组装请求 → 调 REST → 透传结果」，所有计算/分析/存储都在平台侧。
- ❌ **不硬编码 base URL**。平台地址一律走环境变量 `APP_BASE_URL`，仅允许在代码里设一个默认值（见下）。
- ❌ **不加鉴权逻辑**。backend REST 是开放的（登录门只在前端），MCP 直接调 `:8000`，不带 token、不做登录。
- ❌ **不增加传输方式**。只 stdio。
- ❌ **不绕过 REST 直连数据库 / 文件系统**。

## 5. 必须执行

- ✅ 平台地址通过 `APP_BASE_URL` 读取，默认 `http://192.168.88.210:8000`。
- ✅ 每次新增/修改 tool 前，先拉取 `${APP_BASE_URL}/openapi.json` 与 `DESIGN.md` 对照。
- ✅ 每个 MCP tool 必须能一一追溯到一个具体 REST 端点（方法 + 路径）。
- ✅ 契约（openapi）与设计（DESIGN.md）发生漂移时，按 `WORKFLOW.md` 的变更流程处理：先同步契约 → 改设计 → 再改代码。

## 6. 环境信息（参考，非配置源）

- demo UI：`http://192.168.88.210:3000/`（登录 `admin` / `vibecoding2026`，**仅前端登录门**）
- REST 文档（人读）：`http://192.168.88.210:8000/docs`
- 机读契约（唯一权威）：`http://192.168.88.210:8000/openapi.json`
