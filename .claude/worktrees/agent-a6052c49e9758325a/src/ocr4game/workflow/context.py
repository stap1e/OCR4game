"""单次运行上下文。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import structlog

from ocr4game.config import GameProfile, GlobalConfig
from ocr4game.resources import runs_base_dir

if TYPE_CHECKING:
    from ocr4game.perception.fusion import Perception
    from ocr4game.platform.capture import ScreenCapture
    from ocr4game.platform.input_win import InputDriver
    from ocr4game.platform.window import GameWindow


@dataclass
class RunContext:
    profile: GameProfile
    global_cfg: GlobalConfig
    window: GameWindow | None = None
    capture: ScreenCapture | None = None
    input: InputDriver | None = None
    perception: Perception | None = None
    vars: dict = field(default_factory=dict)
    run_dir: Path | None = None
    log: object = field(default_factory=structlog.get_logger)

    def ensure_run_dir(self) -> Path:
        if self.run_dir is not None:
            return self.run_dir
        base = runs_base_dir(self.global_cfg)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = base / f"{self.profile.game_id}_{stamp}"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        return self.run_dir

    def save_failure_shot(self, step_id: str, frame: np.ndarray) -> Path:
        import cv2

        out = self.ensure_run_dir() / f"fail_{step_id}.png"
        cv2.imwrite(str(out), frame)
        return out

    def grab_frame(self) -> np.ndarray:
        assert self.capture is not None
        return self.capture.grab()
