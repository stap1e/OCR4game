from __future__ import annotations

import json
from pathlib import Path

from ocr4game.runtime.trace import NullTraceLogger, TraceLogger


class DummyLog:
    def __init__(self) -> None:
        self.warnings: list[dict] = []

    def warning(self, event: str, **kwargs) -> None:
        self.warnings.append({"event": event, **kwargs})


class NotSerializable:
    pass


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_trace_logger_writes_parseable_jsonl(tmp_path: Path) -> None:
    logger = TraceLogger(tmp_path, "star_rail", "daily")
    logger.log("task_started", status="started", step_index=1, message="开始")
    logger.close()

    records = _read_jsonl(tmp_path / "trace.jsonl")
    assert len(records) == 1
    assert records[0]["event"] == "task_started"
    assert records[0]["game_id"] == "star_rail"
    assert records[0]["task_id"] == "daily"
    assert records[0]["status"] == "started"
    assert records[0]["message"] == "开始"


def test_trace_logger_safely_stringifies_unserializable_values(tmp_path: Path) -> None:
    logger = TraceLogger(tmp_path, "star_rail", "daily")
    value = NotSerializable()
    logger.log("custom", extra={"value": value}, raw=value)
    logger.close()

    record = _read_jsonl(tmp_path / "trace.jsonl")[0]
    assert "NotSerializable" in record["extra"]["value"]
    assert "NotSerializable" in record["extra"]["raw"]


def test_null_trace_logger_is_noop() -> None:
    logger = NullTraceLogger()
    logger.log("anything", value=NotSerializable())
    logger.close()


def test_trace_logger_write_failure_does_not_raise(tmp_path: Path) -> None:
    log = DummyLog()
    logger = TraceLogger(tmp_path, "star_rail", "daily", logger=log)
    assert logger._file is not None
    logger._file.close()

    logger.log("will_fail")

    assert log.warnings
