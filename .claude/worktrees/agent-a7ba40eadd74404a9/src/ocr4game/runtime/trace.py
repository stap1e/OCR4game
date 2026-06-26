"""Runtime JSONL trace logging."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

TRACE_FIELDS = {
    "step_index",
    "step_name",
    "action_index",
    "action_type",
    "status",
    "message",
    "elapsed_ms",
    "retry_count",
    "anchor_name",
    "condition",
    "condition_result",
    "matched_score",
    "matched_bbox",
    "roi",
    "screenshot_path",
}


class NullTraceLogger:
    """No-op trace logger used when tracing is not active."""

    def log(self, event: str, **kwargs: Any) -> None:
        return None

    def close(self) -> None:
        return None


class TraceLogger:
    """Append-only JSONL trace writer for a single run directory."""

    def __init__(
        self,
        run_dir: Path,
        game_id: str,
        task_id: str,
        logger: object | None = None,
    ) -> None:
        self.run_dir = Path(run_dir)
        self.game_id = game_id
        self.task_id = task_id
        self.logger = logger
        self.path = self.run_dir / "trace.jsonl"
        self._closed = False
        self._file = None
        try:
            self.run_dir.mkdir(parents=True, exist_ok=True)
            self._file = self.path.open("a", encoding="utf-8")
        except Exception as exc:  # pragma: no cover - platform/filesystem dependent
            self._warn("trace 初始化失败", exc)
            self._file = None

    def log(self, event: str, **kwargs: Any) -> None:
        if self._closed or self._file is None:
            return

        extra = kwargs.pop("extra", None)
        record: dict[str, Any] = {
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "event": event,
            "game_id": self.game_id,
            "task_id": self.task_id,
            "step_index": None,
            "step_name": None,
            "action_index": None,
            "action_type": None,
            "status": None,
            "message": None,
            "elapsed_ms": None,
            "retry_count": None,
            "anchor_name": None,
            "condition": None,
            "condition_result": None,
            "matched_score": None,
            "matched_bbox": None,
            "roi": None,
            "screenshot_path": None,
            "extra": {},
        }

        for key in list(kwargs):
            if key in TRACE_FIELDS:
                record[key] = kwargs.pop(key)

        if isinstance(extra, dict):
            record["extra"].update(extra)
        elif extra is not None:
            record["extra"]["value"] = extra
        record["extra"].update(kwargs)

        try:
            self._file.write(json.dumps(_safe_json(record), ensure_ascii=False) + "\n")
            self._file.flush()
        except Exception as exc:  # pragma: no cover - platform/filesystem dependent
            self._warn("trace 写入失败", exc)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._file is None:
            return
        try:
            self._file.close()
        except Exception as exc:  # pragma: no cover - platform/filesystem dependent
            self._warn("trace 关闭失败", exc)

    def _warn(self, message: str, exc: Exception) -> None:
        warning = getattr(self.logger, "warning", None)
        if callable(warning):
            try:
                warning(message, error=str(exc))
            except Exception:
                return


def _safe_json(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _safe_json(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set):
        return [_safe_json(item) for item in value]
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


__all__ = ["NullTraceLogger", "TraceLogger"]
