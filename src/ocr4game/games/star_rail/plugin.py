"""崩坏：星穹铁道插件。"""

from __future__ import annotations

import structlog

from ocr4game.games.base import GamePlugin
from ocr4game.perception.fusion import Perception
from ocr4game.platform.capture import ScreenCapture
from ocr4game.platform.input_win import InputDriver
from ocr4game.platform.window import GameWindow
from ocr4game.workflow.context import RunContext

log = structlog.get_logger()


class StarRailPlugin(GamePlugin):
    game_id = "star_rail"

    def preflight(self, ctx: RunContext) -> bool:
        titles = self.profile.window.get("title_contains", [])
        window = GameWindow.find_by_titles(titles)
        if window is None:
            log.error("未找到星穹铁道窗口", titles=titles)
            return False

        ctx.window = window
        w, h = window.client_size()
        expected_w = int(self.profile.resolution.get("width", 2048))
        expected_h = int(self.profile.resolution.get("height", 1152))
        tol = int(self.profile.resolution.get("tolerance", 32))

        if abs(w - expected_w) > tol or abs(h - expected_h) > tol:
            log.warning(
                "客户区分辨率与配置不一致",
                actual=(w, h),
                expected=(expected_w, expected_h),
                tolerance=tol,
                hint="请修改 configs/games/star_rail/profile.yaml 中 resolution",
            )

        jitter = int(ctx.global_cfg.input.get("click_jitter", 3))
        ctx.capture = ScreenCapture(window)
        ctx.input = InputDriver(window, click_jitter=jitter)
        ctx.perception = Perception(self.profile)

        log.info(
            "星穹铁道窗口已绑定",
            title=window.title,
            client_size=(w, h),
        )
        return True
