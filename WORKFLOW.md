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

1. 读 `APP_BASE_URL`（默认 `http://192.168.88.210:8000`）。
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

## 变更流程（平台 API 变更时）

```
平台 API 变了
  → 阶段 1 重新拉 openapi 同步 DESIGN（先改设计）
  → 阶段 2 按新 DESIGN 改代码
  → 阶段 3 重新验收
```

**顺序不可颠倒**：永远先同步契约和设计，再动代码。
