"""可选连通性测试：默认跳过（见 pyproject addopts: -m 'not integration'）。

显式运行：
    pytest -m integration
需能访问 ${APP_BASE_URL}（默认 http://192.168.88.210:8000）。
"""

import pytest

from ai_log_mcp.rest_client import fetch_openapi


@pytest.mark.integration
def test_openapi_reachable():
    spec = fetch_openapi()
    assert isinstance(spec.get("paths"), dict)
    assert len(spec["paths"]) > 0
