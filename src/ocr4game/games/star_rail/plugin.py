"""崩坏：星穹铁道插件。"""

from __future__ import annotations

import structlog

from ocr4game.games.base import GamePlugin
from ocr4game.workflow.context import RunContext

log = structlog.get_logger()


class StarRailPlugin(GamePlugin):
    game_id = "star_rail"

    def preflight(self, ctx: RunContext) -> bool:
        if ctx.window is None:
            log.error("运行时未绑定窗口")
            return False

        w, h = ctx.window.client_size()
        expected_w = self.profile.resolution.width
        expected_h = self.profile.resolution.height
        tol = self.profile.resolution.tolerance

        if abs(w - expected_w) > tol or abs(h - expected_h) > tol:
            log.warning(
                "客户区分辨率与配置不一致",
                actual=(w, h),
                expected=(expected_w, expected_h),
                tolerance=tol,
                hint="请修改 configs/games/star_rail/profile.yaml 中 resolution",
            )

        log.info(
            "星穹铁道窗口已绑定",
            title=ctx.window.title,
            client_size=(w, h),
        )
        return True
