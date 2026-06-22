# WORKFLOW.md — L3 阶段协议

> 服从 `CLAUDE.md`（L1）与 `DESIGN.md`（L2）。本文件定义「做事的阶段与顺序」。

## 阶段 1：契约同步（Contract Sync）

目标：让 `DESIGN.md` 的映射表与真实 openapi 一致。

1. 拉取 `${APP_BASE_URL}/openapi.json`。
2. 遍历 `paths` 下每个 `(path, method)`，按 `DESIGN.md` 第 2 节命名原则生成 tool 名。
3. 填充 `DESIGN.md` 第 3 节映射表：每行只记录 tool 名、方法+路径、入参/出参的**引用位置**、读写类型。
4. 排除 Out of Scope 端点（前端/登录相关）。
5. **漂移处理**：若与现有 DESIGN 不一致，更新 DESIGN，**不要**改代码去迁就旧设计。

✅ 出口条件：DESIGN.md 映射表无 `_TBD_`，每行可在 openapi 中定位。

## 阶段 2：实现（Implement）

目标：按 DESIGN 注册 tools。

1. 读 `APP_BASE_URL`（默认 `http://localhost:8000`）。
2. 用官方 `mcp` SDK + stdio 起 server。
3. 为映射表每一行注册一个 tool，逻辑只有三步：**组装请求 → `httpx` 调 REST → 透传响应**。
4. inputSchema 取自 openapi（见 DESIGN 第 1 节），不手写字段。
5. 统一错误处理与超时（见 DESIGN 第 4 节）。

✅ 出口条件：`tools/list` 能列出映射表中全部 tool；每个 tool 可成功转调对应端点。

## 阶段 3：验收（Acceptance）

逐条对照下表，全绿才算完成。

| # | 检查项 | 通过标准 |
| --- | --- | --- |
| 1 | 红线自检 | 全仓除默认值/README 外无硬编码地址；无鉴权/登录代码；只 stdio |
| 2 | 契约一致 | DESIGN 每个 tool 都能在 openapi 找到对应端点，无臆造字段 |
| 3 | 能起来 | MCP Inspector / stdio 启动，`tools/list` 列出全部工具 |
| 4 | 能打通 | 调一个只读 tool，返回平台 REST 的真实响应 |
| 5 | 可换环境 | 改 `APP_BASE_URL` 后请求目标随之改变，无需改代码 |
| 6 | 注册可用 | 按 README 配置后，Claude/Cursor 能看到并调用这些工具 |

### 本轮验收记录（MVP 收口，对照 PRD §4 A1–A7）

> 执行环境：可直连 `http://localhost:8000`。tag 截至 `step-3d`，本节落盘于 `step-3e`。

| # | 标准 | 结论 | 验证命令 / 证据 |
| --- | --- | --- | --- |
| A1 | 每个 MVP 能力(C1–C4)至少 1 个 tool 在 `tools/list` | ✅ | `python scripts/smoke_stdio.py` → 列出 `chat_query/get_job/health/list_logs` 共 4 个 |
| A2 | 检索类 tool 返回字段同 openapi response，无臆造 | ✅ | 单测 `test_tools_readonly.py` 透传不改字段；实跑 `get_job` 返回 openapi `JobResponse` 字段集 |
| A3 | 分析类产出来自平台 REST（非本地生成） | ✅ | 实跑 `chat_query` 返回平台 `ChatResponse`（answer/citations/redaction…）；代码仅转发，无本地计算 |
| A4 | 改 `APP_BASE_URL` 请求目标随之变，免改码 | ✅ | `APP_BASE_URL=http://example.test:9999 python -c '...make_client().base_url'` → `http://example.test:9999` |
| A5 | 全链路无登录/token | ✅ | `grep -rinE 'token|authorization|bearer|login|password|api[_-]?key' src/` 仅命中注释，无鉴权代码 |
| A6 | 非 2xx 返回结构化错误(status+body)，不吞错 | ✅ | 单测 `test_non_2xx_returns_structured_error`；实跑非法 job_id → `{error,status:422,body}` |
| A7 | openapi 未暴露的能力无对应 tool | ✅ | `tools/list`=4，均映射 DESIGN §3.1 既有端点；upload/gateway 未注册（§3.2 推迟） |

测试总览：`python -m pytest -q` → 16 passed, 1 deselected；`pytest -m integration -q` → 1 passed；`scripts/smoke_stdio.py` → SMOKE OK。

### gateway 只读批次验收记录（step-4a..4d）

> 范围：7 个无参 GET（DESIGN §3.2）。不改已冻结的 4 个核心 tool；不含 gateway 写操作与 upload。

| # | 标准 | 结论 | 验证命令 / 证据 |
| --- | --- | --- | --- |
| G1 | 7 个 gateway 只读 tool 全部注册，tools/list 总数 4→11 | ✅ | `scripts/smoke_stdio.py` 断言 11 个且含 7 个新名 |
| G2 | 每个 tool 有非空、说明返回内容的 description（openapi 无输出 schema） | ✅ | 单测 `test_every_gateway_tool_has_nonempty_description`；README 工具表 |
| G3 | 均为无参 GET，路径正确，原样透传 | ✅ | 参数化单测 `test_gateway_read_ok_passthrough`（断言 method/path/无 body）；7 端点实跑返回真实字段 |
| G4 | 非 2xx 返回结构化错误（DESIGN §4） | ✅ | 单测 `test_gateway_read_non_2xx_structured_error`（502→`{error,status,body}`） |
| G5 | 不改已冻结的 4 个核心 tool 行为 | ✅ | 核心 tool 代码与单测未改；表驱动新增，互不影响 |
| G6 | 仅实现只读，写操作/upload 未引入 | ✅ | `GATEWAY_READS` 仅含 7 个 GET；DESIGN §3.3 仍列 upload + 5 个写端点 |

测试总览（本批后）：`pytest -q` → 26 passed, 1 deselected；`pytest -m integration -q` → 1 passed；`scripts/smoke_stdio.py` → SMOKE OK（11 tools）。

### upload_logs 批次验收记录（step-5a..5c）

> 范围：`POST /logs/upload`（multipart），按 DESIGN §6 方案 C（file_path 首选 / content 兜底，互斥）。重点是 tool 侧前置校验。不改已冻结的 11 个 tool。

| # | 标准 | 结论 | 验证命令 / 证据 |
| --- | --- | --- | --- |
| U1 | tool 注册，tools/list 总数 11→12 | ✅ | `scripts/smoke_stdio.py` 断言 12 个且含 `upload_logs` |
| U2 | schema 取自 openapi（source 枚举 nginx/app/custom） | ✅ | `tools.UPLOAD_SOURCES` 对齐 `Body_upload_logs_upload_post.source`；inputSchema 见代码 |
| U3 | file_path 成功：读盘 → multipart（file 字节+basename+source） | ✅ | 单测 `test_file_path_success_sends_multipart`（断言 content-type、file 字节、文件名、source） |
| U4 | content 成功：内联文本 → multipart（默认 upload.log，未给 source 不发） | ✅ | 单测 `test_content_success_default_filename` |
| U5 | 互斥冲突（都给/都不给）→ 结构化错误，未触达平台 | ✅ | 单测 `test_mutual_exclusion_both` / `_neither`（`requests == []`） |
| U6 | 超大小上限（默认 5MB，可经 UPLOAD_MAX_BYTES 调）→ 结构化错误 | ✅ | 单测 `test_oversize_rejected`（env 设 10 字节） |
| U7 | source 非法枚举 → 结构化错误，不透传 | ✅ | 单测 `test_bad_source_enum` |
| U8 | file_path 不存在/非普通文件 → 结构化错误，不抛栈 | ✅ | 单测 `test_file_path_missing` / `_not_regular_file` |
| U9 | 平台非 2xx → DESIGN §4 结构化错误 | ✅ | 单测 `test_platform_422_structured_error` |
| U10 | 真上传有副作用，隔离在 @integration（默认跳过，一次性极小文件） | ✅ | `test_real_upload_side_effect` 带 `@pytest.mark.integration`；默认 deselected |

测试总览（本批后）：`pytest -q` → 36 passed, 2 deselected；`scripts/smoke_stdio.py` → SMOKE OK（12 tools）。
集成（含真上传副作用）：`pytest -m integration -q` → 2 passed；仅连通性用 `pytest -m integration -k "not upload"`。

### gateway 写操作批次验收记录（step-6a..6c）

> 范围判断：5 个 POST 中，动作类 2 个纳入（§3.3b）；3 个 *-report POST 为 CI-only，Out-of-Scope（§5）。不改已冻结的 12 个 tool。

| # | 标准 | 结论 | 验证命令 / 证据 |
| --- | --- | --- | --- |
| W1 | 范围判断落档：纳入 2 / 排除 3（写明理由） | ✅ | DESIGN §3.3b（纳入）+ §5（CI-only 排除三条理由） |
| W2 | 2 个 tool 注册，tools/list 总数 12→14 | ✅ | `scripts/smoke_stdio.py` 断言 14 个且含 2 个新名 |
| W3 | body schema 现查 openapi、可追溯 | ✅ | `guardrail_test`→`GuardrailTestRequest`；`supply_chain_check`→`SupplyChainCheckRequest`（必填 marketplace/item_id，可选 version） |
| W4 | guardrail_test 透传 + body 正确 | ✅ | 单测 `test_guardrail_test_ok_and_body`；实跑注入文本→`verdict=BLOCKED` |
| W5 | supply_chain_check 透传；version 仅在提供时发 | ✅ | 单测 `test_supply_chain_check_ok_with_version` / `_omits_absent_version`；实跑 pypi/httpx→真实判定 |
| W6 | 平台非 2xx → DESIGN §4 结构化错误 | ✅ | 单测 `test_guardrail_test_non_2xx_structured_error`（422） |
| W7 | 不做改平台状态的默认 integration | ✅ | 本批未加 integration 用例；实跑仅一次性人工验证（observability 计数+2，无业务数据写入） |

测试总览（本批后）：`pytest -q` → 41 passed, 2 deselected；`scripts/smoke_stdio.py` → SMOKE OK（14 tools）。

## 变更流程（平台 API 变更时）

```
平台 API 变了
  → 阶段 1 重新拉 openapi 同步 DESIGN（先改设计）
  → 阶段 2 按新 DESIGN 改代码
  → 阶段 3 重新验收
```

**顺序不可颠倒**：永远先同步契约和设计，再动代码。
