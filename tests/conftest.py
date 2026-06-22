"""测试脚手架：用 httpx.MockTransport mock REST 层，单测不依赖 210 在线。

核心 fixture `mock_rest`：注册 (METHOD, PATH) -> 响应，monkeypatch 掉
rest_client.make_client，使被测代码走 mock 传输而非真实网络。
"""

import json as _json

import httpx
import pytest

from ai_log_mcp import rest_client


class _Router:
    """收集路由并构造 httpx.MockTransport。"""

    def __init__(self):
        self._routes = {}
        self.requests = []  # 记录收到的请求，供断言 body 组装

    def add(self, method: str, path: str, *, status: int = 200, json=None, text=None):
        """注册一个 mock 响应。json/text 二选一。"""
        self._routes[(method.upper(), path)] = (status, json, text)

    def _handler(self, request: httpx.Request) -> httpx.Response:
        try:
            body = _json.loads(request.content) if request.content else None
        except ValueError:
            body = None
        self.requests.append({"method": request.method.upper(), "path": request.url.path,
                              "params": dict(request.url.params), "json": body})
        key = (request.method.upper(), request.url.path)
        if key not in self._routes:
            return httpx.Response(404, json={"detail": f"no mock for {key}"})
        status, body, text = self._routes[key]
        if text is not None:
            return httpx.Response(status, text=text)
        return httpx.Response(status, content=_json.dumps(body).encode(), headers={"content-type": "application/json"})

    def client(self) -> httpx.Client:
        return httpx.Client(base_url="http://mock", transport=httpx.MockTransport(self._handler))


@pytest.fixture
def mock_rest(monkeypatch):
    """返回 _Router；测试用 .add(...) 注册响应，已自动接管 make_client。"""
    router = _Router()
    monkeypatch.setattr(rest_client, "make_client", router.client)
    return router
