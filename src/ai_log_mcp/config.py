"""配置读取：平台地址走环境变量，不硬编码（见 CLAUDE.md 红线）。"""

import os

# 仅此一处默认值（与 .env.example / README 保持一致）。
DEFAULT_BASE_URL = "http://localhost:8000"

# upload_logs 字节上限默认 5 MB（见 DESIGN §6.4）。
DEFAULT_UPLOAD_MAX_BYTES = 5 * 1024 * 1024


def get_base_url() -> str:
    """返回平台 REST 基址。优先读 APP_BASE_URL，缺省回退默认 demo 地址。"""
    return os.environ.get("APP_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def get_upload_max_bytes() -> int:
    """upload_logs 允许的最大字节数。读 UPLOAD_MAX_BYTES，缺省/非法回退默认值。"""
    raw = os.environ.get("UPLOAD_MAX_BYTES")
    if raw is None:
        return DEFAULT_UPLOAD_MAX_BYTES
    try:
        val = int(raw)
        return val if val > 0 else DEFAULT_UPLOAD_MAX_BYTES
    except ValueError:
        return DEFAULT_UPLOAD_MAX_BYTES
