"""配置读取：平台地址走环境变量，不硬编码（见 CLAUDE.md 红线）。"""

import os

# 仅此一处默认值（与 .env.example / README 保持一致）。
DEFAULT_BASE_URL = "http://192.168.88.210:8000"


def get_base_url() -> str:
    """返回平台 REST 基址。优先读 APP_BASE_URL，缺省回退默认 demo 地址。"""
    return os.environ.get("APP_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
