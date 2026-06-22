"""网关安全·只读 tool 单测（mock REST，不依赖 210）。

覆盖：注册、无参 GET 透传、路径正确、非 2xx 结构化错误。
"""

import pytest

from ai_log_mcp import tools

# step-4b 批次（网关状态/配置）
BATCH_4B = {
    "gateway_observability": "/gateway/observability",
    "gateway_info": "/gateway/info",
    "gateway_prompts": "/gateway/prompts",
}


def test_batch_4b_registered():
    names = {t.name for t in tools.TOOLS}
    assert set(BATCH_4B) <= names


@pytest.mark.parametrize("name,path", list(BATCH_4B.items()))
def test_gateway_read_ok_passthrough(mock_rest, name, path):
    payload = {"sentinel": name}
    mock_rest.add("GET", path, json=payload)
    assert tools.call(name, {}) == payload
    assert mock_rest.requests[-1] == {"method": "GET", "path": path, "params": {}, "json": None}


def test_gateway_read_non_2xx_structured_error(mock_rest):
    mock_rest.add("GET", "/gateway/info", status=502, json={"detail": "bad gateway"})
    out = tools.call("gateway_info", {})
    assert out == {"error": True, "status": 502, "body": {"detail": "bad gateway"}}


def test_every_gateway_tool_has_nonempty_description():
    # openapi 无输出 schema，description 是调用方唯一依据，不允许为空。
    for t in tools.TOOLS:
        if t.name.startswith("gateway_"):
            assert t.description and len(t.description) > 10
