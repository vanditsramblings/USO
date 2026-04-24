"""Tests for uso.file_manager module."""

import pytest

from uso.file_manager import (
    CleanupHook,
    NotifyHook,
    RetainHook,
    VersionHook,
    collect_artifacts,
    get_output_dir,
    save_upload,
    sha256_digest,
)


def test_sha256_digest():
    assert len(sha256_digest(b"hello")) == 64


def test_save_upload(tmp_path, monkeypatch):
    monkeypatch.setattr("uso.file_manager.UPLOAD_DIR", tmp_path / "uploads")
    result = save_upload("test.txt", b"file content here")
    assert result["sha256"] == sha256_digest(b"file content here")
    assert result["size_bytes"] == len(b"file content here")
    assert (tmp_path / "uploads").exists()


def test_save_upload_too_large(tmp_path, monkeypatch):
    monkeypatch.setattr("uso.file_manager.UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr("uso.file_manager.MAX_UPLOAD_BYTES", 10)
    with pytest.raises(ValueError, match="exceeds"):
        save_upload("big.bin", b"x" * 20)


def test_get_output_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("uso.file_manager.OUTPUT_DIR", tmp_path / "outputs")
    out = get_output_dir("my-script", "run-123")
    assert out.exists()
    assert "my-script" in str(out)


def test_collect_artifacts(tmp_path):
    (tmp_path / "result.csv").write_bytes(b"a,b,c")
    (tmp_path / "log.txt").write_bytes(b"done")
    arts = collect_artifacts(tmp_path)
    assert len(arts) == 2
    assert arts[0]["filename"] == "log.txt"
    assert arts[1]["filename"] == "result.csv"
    assert all(a["sha256"] for a in arts)


def test_collect_artifacts_empty(tmp_path):
    assert collect_artifacts(tmp_path / "nonexistent") == []


def test_retain_hook(tmp_path):
    out_dir = tmp_path / "outputs" / "test-run"
    out_dir.mkdir(parents=True)
    (out_dir / "data.txt").write_text("result")
    archive_dir = tmp_path / "archives"
    hook = RetainHook(archive_dir=archive_dir)
    hook.fire("run-1", "test-script", "success", out_dir)
    assert any(f.suffix == ".zip" for f in archive_dir.iterdir())


def test_retain_hook_skips_failure(tmp_path):
    out_dir = tmp_path / "outputs"
    out_dir.mkdir()
    archive_dir = tmp_path / "archives"
    hook = RetainHook(archive_dir=archive_dir)
    hook.fire("run-1", "s", "failure", out_dir)
    assert not archive_dir.exists()


def test_cleanup_hook(tmp_path):
    out_dir = tmp_path / "outputs"
    out_dir.mkdir()
    (out_dir / "f.txt").write_text("x")
    hook = CleanupHook()
    hook.fire("run-1", "s", "success", out_dir)
    assert not out_dir.exists()


def test_notify_hook_calls_callback():
    messages = []
    hook = NotifyHook(callback=messages.append)
    hook.fire("run-1", "broken-script", "failure", None)
    assert len(messages) == 1
    assert "broken-script" in messages[0]


def test_notify_hook_skips_success():
    messages = []
    hook = NotifyHook(callback=messages.append)
    hook.fire("run-1", "s", "success", None)
    assert len(messages) == 0


def test_version_hook(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("uso.db.connection.DEFAULT_DB_PATH", db_path)
    import uso.db as db_mod

    if hasattr(db_mod._local, "connections"):
        db_mod._local.connections.clear()
    db_mod.init_db(db_path)

    sid = db_mod.create_script("vhook", "sh", "echo hi")
    rid = db_mod.create_run(sid)

    out_dir = tmp_path / "run_out"
    out_dir.mkdir()
    (out_dir / "report.txt").write_bytes(b"data here")

    hook = VersionHook()
    hook.fire(rid, "vhook", "success", out_dir)
    arts = db_mod.get_artifacts(rid)
    assert len(arts) == 1
    assert arts[0]["filename"] == "report.txt"
