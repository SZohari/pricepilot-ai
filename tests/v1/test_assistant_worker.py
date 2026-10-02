"""Exercise real process boundaries without downloading a model in unit tests."""
import time
import pytest
from src.infrastructure import assistant_worker as worker


def reply_then_hang(connection, path):
    connection.recv()
    connection.send({'answer': {'explanation': 'A test response.', 'source_ids': ['test']}})
    connection.recv()
    time.sleep(30)


def exit_without_reply(connection, path):
    connection.close()


def test_worker_reuses_process_and_terminates_a_stuck_native_call(monkeypatch):
    worker.stop_worker()
    monkeypatch.setattr(worker, '_serve', reply_then_hang)
    try:
        assert worker.request_generation('test.gguf', [], {}, timeout=10)['source_ids'] == ['test']
        started = time.monotonic()
        with pytest.raises(TimeoutError):
            worker.request_generation('test.gguf', [], {}, timeout=.1)
        assert time.monotonic()-started < 4
        assert worker._process is None and worker._connection is None
    finally:
        worker.stop_worker()


def test_native_worker_crash_is_a_recoverable_error(monkeypatch):
    worker.stop_worker()
    monkeypatch.setattr(worker, '_serve', exit_without_reply)
    try:
        with pytest.raises(OSError):
            worker.request_generation('test.gguf', [], {}, timeout=10)
        assert worker._process is None
    finally:
        worker.stop_worker()
