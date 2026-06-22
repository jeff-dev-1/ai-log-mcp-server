"""rest_client.fetch_openapi：走 mock 传输，验证成功与非 2xx 行为。"""

import httpx
import pytest

from ai_log_mcp import rest_client


def test_fetch_openapi_ok(mock_rest):
    mock_rest.add("GET", "/openapi.json", json={"paths": {"/logs": {}}})
    spec = rest_client.fetch_openapi()
    assert "paths" in spec


def test_fetch_openapi_non_2xx_raises(mock_rest):
    mock_rest.add("GET", "/openapi.json", status=500, json={"detail": "boom"})
    with pytest.raises(httpx.HTTPStatusError):
        rest_client.fetch_openapi()
