"""连通性自检：能拉到 ${APP_BASE_URL}/openapi.json 即视为通，为 WORKFLOW 阶段 1 铺路。

用法:
    python -m ai_log_mcp.check
退出码:
    0 = 通（打印 base url 与 path 数量）
    1 = 不通（打印错误）
"""

import sys

import httpx

from .config import get_base_url
from .rest_client import fetch_openapi


def main() -> int:
    base = get_base_url()
    try:
        spec = fetch_openapi()
    except httpx.HTTPError as exc:
        print(f"FAIL: cannot reach {base}/openapi.json -> {exc}", file=sys.stderr)
        return 1

    paths = spec.get("paths", {})
    print(f"OK: {base}/openapi.json reachable, {len(paths)} paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
