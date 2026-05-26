"""屏幕捕获：优先游戏窗口客户区。"""

from __future__ import annotations

import numpy as np
import mss
import cv2

from ocr4game.platform.window import GameWindow


class ScreenCapture:
    def __init__(self, window: GameWindow | None = None) -> None:
        self._window = window
        self._mss = mss.mss()

    def set_window(self, window: GameWindow | None) -> None:
        self._window = window

    def grab(self) -> np.ndarray:
        if self._window is not None:
            left, top, right, bottom = self._window.client_rect_screen()
            monitor = {
                "left": left,
                "top": top,
                "width": right - left,
                "height": bottom - top,
            }
        else:
            monitor = self._mss.monitors[1]

        shot = self._mss.grab(monitor)
        frame = np.array(shot)
        # BGRA -> BGR
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
