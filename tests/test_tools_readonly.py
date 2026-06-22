"""核心只读 tool 单测：list_logs / get_job / health（mock REST，不依赖 210）。"""

from ai_log_mcp import tools


def test_tools_registered():
    names = {t.name for t in tools.TOOLS}
    assert {"list_logs", "get_job", "health"} <= names


def test_list_logs_ok(mock_rest):
    mock_rest.add("GET", "/logs", json=[{"job_id": "a"}, {"job_id": "b"}])
    out = tools.call("list_logs", {})
    assert out == [{"job_id": "a"}, {"job_id": "b"}]


def test_list_logs_passthrough_no_mutation(mock_rest):
    payload = [{"job_id": "x", "extra": 1}]
    mock_rest.add("GET", "/logs", json=payload)
    assert tools.call("list_logs", {"limit": 5}) == payload


def test_get_job_ok(mock_rest):
    mock_rest.add("GET", "/logs/jobs/job123", json={"job_id": "job123", "status": "done"})
    out = tools.call("get_job", {"job_id": "job123"})
    assert out["job_id"] == "job123"


def test_health_ok(mock_rest):
    mock_rest.add("GET", "/health", json={"status": "ok"})
    assert tools.call("health", {}) == {"status": "ok"}


def test_non_2xx_returns_structured_error(mock_rest):
    mock_rest.add("GET", "/logs", status=503, json={"detail": "unavailable"})
    out = tools.call("list_logs", {})
    assert out == {"error": True, "status": 503, "body": {"detail": "unavailable"}}


def test_unknown_tool_raises():
    import pytest

    with pytest.raises(ValueError):
        tools.call("nope", {})
