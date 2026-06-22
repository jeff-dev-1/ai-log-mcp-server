"""chat_query 单测：body 组装、透传、非 2xx 结构化错误（mock REST）。"""

from ai_log_mcp import tools


def test_chat_query_registered():
    assert "chat_query" in {t.name for t in tools.TOOLS}


def test_chat_query_ok_and_passthrough(mock_rest):
    mock_rest.add("POST", "/chat/query", json={"answer": "hi", "citations": []})
    out = tools.call("chat_query", {"question": "为什么报错?"})
    assert out == {"answer": "hi", "citations": []}


def test_chat_query_body_only_provided_fields(mock_rest):
    mock_rest.add("POST", "/chat/query", json={"answer": "ok"})
    tools.call("chat_query", {"question": "q", "top_k": 3, "backend": "qwen"})
    sent = mock_rest.requests[-1]["json"]
    # 只带显式提供的字段，不臆造 log_id/scenario 等缺省。
    assert sent == {"question": "q", "top_k": 3, "backend": "qwen"}


def test_chat_query_non_2xx_structured_error(mock_rest):
    mock_rest.add("POST", "/chat/query", status=422, json={"detail": "bad"})
    out = tools.call("chat_query", {"question": "q"})
    assert out == {"error": True, "status": 422, "body": {"detail": "bad"}}
