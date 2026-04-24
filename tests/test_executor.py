"""Tests for uso.executor module."""

import queue

import pytest

from uso.executor import SubprocessExecutor


@pytest.fixture()
def executor():
    return SubprocessExecutor()


def test_run_python_script(executor):
    result = executor.run(b"print('hello from python')", runtime="py", timeout=10)
    assert result["exit_code"] == 0
    assert result["status"] == "success"
    assert "hello from python" in result["logs"]


def test_run_shell_script(executor):
    result = executor.run(b"echo 'hello from shell'", runtime="sh", timeout=10)
    assert result["exit_code"] == 0
    assert "hello from shell" in result["logs"]


def test_run_failing_script(executor):
    result = executor.run(b"exit 1", runtime="sh", timeout=10)
    assert result["exit_code"] == 1
    assert result["status"] == "failure"


def test_run_timeout(executor):
    result = executor.run(b"import time; time.sleep(30)", runtime="py", timeout=2)
    assert result["status"] == "timeout"


def test_run_with_env(executor):
    script = b"import os; print(os.environ.get('TEST_VAR', 'missing'))"
    result = executor.run(script, runtime="py", env={"TEST_VAR": "hello"}, timeout=10)
    assert "hello" in result["logs"]


def test_env_isolation(executor):
    script = b"import os; print(os.environ.get('HOME', 'NOT_SET'))"
    result = executor.run(script, runtime="py", timeout=10)
    assert "NOT_SET" in result["logs"]


def test_unsupported_runtime(executor):
    with pytest.raises(ValueError, match="Unsupported runtime"):
        executor.run(b"puts 'hi'", runtime="rb")


def test_stderr_captured(executor):
    script = b"import sys; print('err', file=sys.stderr)"
    result = executor.run(script, runtime="py", timeout=10)
    assert "[stderr]" in result["logs"]


def test_streaming_mode(executor):
    log_queue: queue.Queue = queue.Queue()
    result = executor.run_streaming(
        b"print('streamed')", runtime="py", log_queue=log_queue, timeout=10
    )
    assert result["status"] == "success"
    lines = []
    while not log_queue.empty():
        lines.append(log_queue.get_nowait())
    assert any("streamed" in line for line in lines)
