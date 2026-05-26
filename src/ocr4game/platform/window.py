"""Windows 游戏窗口查找与客户区坐标。"""

from __future__ import annotations

from dataclasses import dataclass

import win32con
import win32gui


@dataclass
class GameWindow:
    hwnd: int
    title: str

    @classmethod
    def find_by_titles(cls, title_substrings: list[str]) -> GameWindow | None:
        found: list[tuple[int, str]] = []

        def callback(hwnd: int, _: object) -> bool:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return True
            for sub in title_substrings:
                if sub in title:
                    found.append((hwnd, title))
                    return False
            return True

        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            pass

        if not found:
            return None
        hwnd, title = found[0]
        return cls(hwnd=hwnd, title=title)

    def focus(self) -> None:
        try:
            win32gui.SetForegroundWindow(self.hwnd)
        except Exception:
            pass

    def client_rect_screen(self) -> tuple[int, int, int, int]:
        """客户区在屏幕上的 (left, top, right, bottom)。"""
        left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
        pt = win32gui.ClientToScreen(self.hwnd, (left, top))
        width = right - left
        height = bottom - top
        return pt[0], pt[1], pt[0] + width, pt[1] + height

    def client_size(self) -> tuple[int, int]:
        left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
        return right - left, bottom - top

    def screen_to_client(self, x: int, y: int) -> tuple[int, int]:
        return win32gui.ScreenToClient(self.hwnd, (x, y))
