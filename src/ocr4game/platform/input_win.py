"""Windows 输入：DirectInput 风格点击与按键。"""

from __future__ import annotations

import random
import time

import pydirectinput

from ocr4game.platform.window import GameWindow

pydirectinput.PAUSE = 0.02


class InputDriver:
    def __init__(self, window: GameWindow | None = None, click_jitter: int = 3) -> None:
        self._window = window
        self._click_jitter = click_jitter

    def set_window(self, window: GameWindow | None) -> None:
        self._window = window

    def _to_screen(self, x: int, y: int) -> tuple[int, int]:
        if self._window is None:
            return x, y
        left, top, _, _ = self._window.client_rect_screen()
        return left + x, top + y

    def click(self, x: int, y: int, *, client_coords: bool = True) -> None:
        if self._window:
            self._window.focus()
        if client_coords:
            sx, sy = self._to_screen(x, y)
        else:
            sx, sy = x, y
        j = self._click_jitter
        if j > 0:
            sx += random.randint(-j, j)
            sy += random.randint(-j, j)
        pydirectinput.click(sx, sy)

    def press(self, key: str) -> None:
        if self._window:
            self._window.focus()
        pydirectinput.press(key)

    def sleep_ms(self, ms: int) -> None:
        time.sleep(ms / 1000.0)
