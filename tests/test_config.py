"""config.get_base_url：环境变量优先，缺省回退默认值，去尾斜杠。"""

from ai_log_mcp import config


def test_default_when_unset(monkeypatch):
    monkeypatch.delenv("APP_BASE_URL", raising=False)
    assert config.get_base_url() == config.DEFAULT_BASE_URL


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("APP_BASE_URL", "http://example:9000")
    assert config.get_base_url() == "http://example:9000"


def test_strips_trailing_slash(monkeypatch):
    monkeypatch.setenv("APP_BASE_URL", "http://example:9000/")
    assert config.get_base_url() == "http://example:9000"
