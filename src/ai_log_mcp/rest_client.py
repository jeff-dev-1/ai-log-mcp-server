"""平台 REST 的薄封装：只负责发请求，不含任何业务逻辑（见 CLAUDE.md 红线）。

- base URL 走 config.get_base_url()，不硬编码。
- 不带鉴权 token（backend REST 开放，登录门只在前端）。
"""

import httpx

from .config import get_base_url

DEFAULT_TIMEOUT = 30.0


def make_client() -> httpx.Client:
    """构造指向平台的 httpx 客户端。base_url 随 APP_BASE_URL 变化。"""
    return httpx.Client(base_url=get_base_url(), timeout=DEFAULT_TIMEOUT)


def fetch_openapi() -> dict:
    """拉取 ${APP_BASE_URL}/openapi.json —— 阶段 1 契约同步与连通性自检的入口。"""
    with make_client() as client:
        resp = client.get("/openapi.json")
        resp.raise_for_status()
        return resp.json()


def _body(resp: httpx.Response):
    """body 优先按 JSON 解析，失败则回退原始文本。"""
    try:
        return resp.json()
    except ValueError:
        return resp.text


def request_json(method: str, path: str, *, params: dict | None = None, json: dict | None = None):
    """发一次 REST 请求，返回 (status_code, body)。

    - 不抛非 2xx（交给上层 tool 按 DESIGN §4 组装结构化错误）。
    - body 优先按 JSON 解析，失败则回退原始文本。
    """
    with make_client() as client:
        resp = client.request(method, path, params=params, json=json)
        return resp.status_code, _body(resp)


def request_multipart(method: str, path: str, *, files: dict, data: dict | None = None):
    """发一次 multipart/form-data 请求，返回 (status_code, body)。

    files / data 直接透传给 httpx（见 DESIGN §6.1：file 走 files，source 走 data）。
    同样不抛非 2xx。
    """
    with make_client() as client:
        resp = client.request(method, path, files=files, data=data)
        return resp.status_code, _body(resp)
