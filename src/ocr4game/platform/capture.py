"""屏幕捕获：优先 PrintWindow，避免被终端/IDE 遮挡。"""

from __future__ import annotations

import time
from ctypes import windll

import cv2
import mss
import numpy as np
import win32gui
import win32ui

from ocr4game.platform.window import GameWindow

PW_RENDERFULLCONTENT = 2


class ScreenCapture:
    def __init__(self, window: GameWindow | None = None) -> None:
        self._window = window
        self._mss = mss.mss()

    def set_window(self, window: GameWindow | None) -> None:
        self._window = window

    def grab(self) -> np.ndarray:
        if self._window is not None:
            self._window.focus()
            time.sleep(0.2)
            frame = self._grab_print_window(self._window)
            if frame is not None:
                return frame
            return self._grab_mss(self._window)
        return self._grab_mss(None)

    def _grab_print_window(self, window: GameWindow) -> np.ndarray | None:
        hwnd = window.capture_hwnd()
        hwnd_dc = None
        save_dc = None
        mfc_dc = None
        bitmap = None
        try:
            left, top, right, bottom = win32gui.GetClientRect(hwnd)
            width = right - left
            height = bottom - top
            if width <= 0 or height <= 0:
                return None

            hwnd_dc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(bitmap)

            ok = windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), PW_RENDERFULLCONTENT)
            if ok != 1:
                ok = windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 0)
            if ok != 1:
                return None

            bmpstr = bitmap.GetBitmapBits(True)
            img = np.frombuffer(bmpstr, dtype=np.uint8)
            img.shape = (height, width, 4)
            bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            if float(bgr.mean()) < 1.0:
                return None
            return bgr
        except Exception:
            return None
        finally:
            if bitmap is not None:
                win32gui.DeleteObject(bitmap.GetHandle())
            if save_dc is not None:
                save_dc.DeleteDC()
            if mfc_dc is not None:
                mfc_dc.DeleteDC()
            if hwnd_dc is not None:
                win32gui.ReleaseDC(hwnd, hwnd_dc)

    def _grab_mss(self, window: GameWindow | None) -> np.ndarray:
        if window is not None:
            left, top, right, bottom = window.client_rect_screen()
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
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
