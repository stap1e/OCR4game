"""配置模型与加载。"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, Field

from ocr4game.resources import game_profile_path, global_config_path

RelativeRoi = Annotated[list[float], Field(min_length=4, max_length=4)]


class CaptureConfig(BaseModel):
    backend: str = "mss"
    fps_limit: int = 10


class InputConfig(BaseModel):
    click_jitter: int = 3
    default_delay_ms: int = 80


class WorkflowDefaultsConfig(BaseModel):
    default_step_timeout_ms: int = 10000
    default_max_retry: int = 3
    max_run_minutes: int = 45


class WindowConfig(BaseModel):
    title_contains: list[str] = Field(default_factory=list)
    title_exclude: list[str] = Field(default_factory=list)
    class_exclude: list[str] = Field(default_factory=list)
    process_names: list[str] = Field(default_factory=list)


class ResolutionConfig(BaseModel):
    width: int = 2048
    height: int = 1152
    tolerance: int = 32


class PathsConfig(BaseModel):
    assets: str = "assets"
    tasks: str = "tasks"


class RecoveryConfig(BaseModel):
    escape_key: str = "escape"
    max_recovery_attempts: int = 2


class TemplateAnchorConfig(BaseModel):
    type: Literal["template"] = "template"
    image: str
    threshold: float = 0.85
    roi: RelativeRoi | None = None
    scales: list[float] = Field(default_factory=lambda: [1.0])
    match_mode: Literal["color", "gray", "edges"] = "gray"


class OcrAnchorConfig(BaseModel):
    type: Literal["ocr"] = "ocr"
    expect: list[str] = Field(default_factory=list)
    roi: RelativeRoi | None = None
    min_confidence: float = 0.5


AnchorConfig = TemplateAnchorConfig | OcrAnchorConfig


class GlobalConfig(BaseModel):
    log_level: str = "INFO"
    runs_dir: str = "runs"
    capture: CaptureConfig = Field(default_factory=CaptureConfig)
    input: InputConfig = Field(default_factory=InputConfig)
    workflow: WorkflowDefaultsConfig = Field(default_factory=WorkflowDefaultsConfig)


class GameProfile(BaseModel):
    game_id: str
    display_name: str = ""
    window: WindowConfig = Field(default_factory=WindowConfig)
    resolution: ResolutionConfig = Field(default_factory=ResolutionConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    anchors: dict[str, AnchorConfig] = Field(default_factory=dict)
    recovery: RecoveryConfig = Field(default_factory=RecoveryConfig)
    extensions: dict[str, Any] = Field(default_factory=dict)


class StepBlock(BaseModel):
    id: str
    do: list[dict[str, Any]] = Field(min_length=1)
    when: dict[str, Any] | None = None
    loop: dict[str, Any] | int | None = None
    repeat: int | str | None = None
    retry: int | None = None


class TaskConfig(BaseModel):
    name: str = ""
    description: str = ""
    vars: dict[str, Any] = Field(default_factory=dict)
    steps: list[StepBlock] = Field(min_length=1)
    extensions: dict[str, Any] = Field(default_factory=dict)


def load_task_config(path: Path) -> TaskConfig:
    return TaskConfig.model_validate(load_yaml(path))


def load_global_config() -> GlobalConfig:
    path = global_config_path()
    if not path.exists():
        return GlobalConfig()
    return GlobalConfig.model_validate(load_yaml(path))


def load_game_profile(game_id: str) -> GameProfile:
    path = game_profile_path(game_id)
    data = load_yaml(path)
    data.setdefault("game_id", game_id)
    return GameProfile.model_validate(data)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


__all__ = [
    "AnchorConfig",
    "CaptureConfig",
    "GameProfile",
    "GlobalConfig",
    "InputConfig",
    "OcrAnchorConfig",
    "PathsConfig",
    "RecoveryConfig",
    "RelativeRoi",
    "ResolutionConfig",
    "TaskConfig",
    "StepBlock",
    "TemplateAnchorConfig",
    "WindowConfig",
    "WorkflowDefaultsConfig",
    "load_game_profile",
    "load_global_config",
    "load_task_config",
    "load_yaml",
]
