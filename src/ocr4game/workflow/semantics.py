"""Shared workflow step and action semantics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ParsedAction:
    name: str
    params: Any


@dataclass(frozen=True)
class StepRuntimeConfig:
    actions: list[dict[str, Any]]
    loop_max: int | None
    repeat: int | None
    retry: int


def parse_action(action: dict[str, Any]) -> ParsedAction:
    if not isinstance(action, dict) or len(action) != 1:
        raise ValueError(f"动作必须是单键 dict: {action!r}")
    name, params = next(iter(action.items()))
    return ParsedAction(name=name, params=params)


def parse_step_runtime(block: dict[str, Any], *, default_retry: int) -> StepRuntimeConfig:
    actions = block.get("do") or []
    loop_cfg = block.get("loop")
    repeat_cfg = block.get("repeat")
    retry_raw = block.get("retry")

    loop_max = None
    if loop_cfg is not None:
        loop_max = int(loop_cfg) if isinstance(loop_cfg, int) else int(loop_cfg.get("max", 10))

    repeat = None if repeat_cfg is None else int(repeat_cfg)
    retry = int(retry_raw if retry_raw is not None else default_retry)

    return StepRuntimeConfig(
        actions=actions,
        loop_max=loop_max,
        repeat=repeat,
        retry=retry,
    )
