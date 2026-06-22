"""upload_logs 单测：前置校验是重点，全程 mock REST（不打 210）。

覆盖六路：file_path 成功 / content 成功 / 互斥错误 / 超限 / 枚举非法 / 平台 422。
另含 file_path 不存在 / 非普通文件。

注意：真实上传有副作用（在平台创建真任务、污染数据）。单测一律 mock，
真上传见文末 @integration（默认跳过，且用一次性极小文件）。
"""

import pytest

from ai_log_mcp import tools

UPLOAD_PATH = "/logs/upload"


def test_upload_logs_registered():
    assert "upload_logs" in {t.name for t in tools.TOOLS}


def test_file_path_success_sends_multipart(mock_rest, tmp_path):
    f = tmp_path / "access.log"
    f.write_bytes(b"127.0.0.1 - GET /x 200")
    mock_rest.add("POST", UPLOAD_PATH, json={"job_id": "j1", "status": "queued"})

    out = tools.call("upload_logs", {"file_path": str(f), "source": "nginx"})

    assert out == {"job_id": "j1", "status": "queued"}  # 原样透传 UploadResponse
    req = mock_rest.requests[-1]
    assert req["path"] == UPLOAD_PATH
    assert req["content_type"].startswith("multipart/form-data")
    assert b"127.0.0.1 - GET /x 200" in req["raw"]   # file 字节
    assert b"access.log" in req["raw"]                # 文件名取 basename
    assert b"nginx" in req["raw"]                     # source 走 form


def test_content_success_default_filename(mock_rest):
    mock_rest.add("POST", UPLOAD_PATH, json={"job_id": "j2"})

    out = tools.call("upload_logs", {"content": "hello log line"})

    assert out == {"job_id": "j2"}
    req = mock_rest.requests[-1]
    assert req["content_type"].startswith("multipart/form-data")
    assert b"hello log line" in req["raw"]
    assert b"upload.log" in req["raw"]                # content 缺省文件名
    assert b"source" not in req["raw"]               # 未提供 source 则不发


def test_mutual_exclusion_both(mock_rest):
    out = tools.call("upload_logs", {"file_path": "/x", "content": "y"})
    assert out["error"] is True and out["status"] == "validation_error"
    assert mock_rest.requests == []                  # 未触达平台


def test_mutual_exclusion_neither(mock_rest):
    out = tools.call("upload_logs", {})
    assert out["status"] == "validation_error"
    assert mock_rest.requests == []


def test_oversize_rejected(mock_rest, monkeypatch):
    monkeypatch.setenv("UPLOAD_MAX_BYTES", "10")
    out = tools.call("upload_logs", {"content": "x" * 50})
    assert out["status"] == "validation_error"
    assert "上限" in out["body"]["detail"]
    assert mock_rest.requests == []


def test_bad_source_enum(mock_rest):
    out = tools.call("upload_logs", {"content": "hi", "source": "bogus"})
    assert out["status"] == "validation_error"
    assert mock_rest.requests == []


def test_file_path_missing(mock_rest):
    out = tools.call("upload_logs", {"file_path": "/definitely/no/such/file.log"})
    assert out["status"] == "validation_error"
    assert "不存在" in out["body"]["detail"]


def test_file_path_not_regular_file(mock_rest, tmp_path):
    out = tools.call("upload_logs", {"file_path": str(tmp_path)})  # 目录
    assert out["status"] == "validation_error"
    assert "普通文件" in out["body"]["detail"]


def test_platform_422_structured_error(mock_rest):
    mock_rest.add("POST", UPLOAD_PATH, status=422, json={"detail": [{"msg": "bad"}]})
    out = tools.call("upload_logs", {"content": "hi"})
    assert out == {"error": True, "status": 422, "body": {"detail": [{"msg": "bad"}]}}


# ── 真上传（有副作用！默认跳过）────────────────────────────────────────────────
@pytest.mark.integration
def test_real_upload_side_effect():
    """⚠️ 有副作用：会在平台真实创建一条任务、污染数据。

    用一次性极小内容；仅在 `pytest -m integration` 时运行。
    """
    out = tools.call("upload_logs", {"content": "smoke upload one-shot\n", "source": "custom"})
    assert not (isinstance(out, dict) and out.get("error")), out
