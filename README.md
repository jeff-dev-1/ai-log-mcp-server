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
# 1. 安装依赖（实现阶段产出 pyproject.toml 后）
pip install -e .

# 2. 指定平台地址（不指定则用默认 demo 地址）
export APP_BASE_URL="http://192.168.88.210:8000"

# 3. 以 stdio 方式启动 MCP server
python -m ai_log_mcp.server
```

> 调试推荐用 MCP Inspector：`npx @modelcontextprotocol/inspector python -m ai_log_mcp.server`

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

## 参考链接

- demo UI：http://192.168.88.210:3000/ （登录 `admin` / `vibecoding2026`，仅前端）
- REST 文档（人读）：http://192.168.88.210:8000/docs
- 机读契约（唯一权威）：http://192.168.88.210:8000/openapi.json
