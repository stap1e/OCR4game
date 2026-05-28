"""Windows 游戏窗口查找与客户区坐标。"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

import win32api
import win32con
import win32gui
import win32process

# 终端/IDE 等窗口类名，不应作为游戏窗口
DEFAULT_CLASS_EXCLUDE = frozenset(
    {
        "ConsoleWindowClass",
        "CASCADIA_HOSTING_WINDOW_CLASS",
        "CascadiaWindowClass",
        "MinttyClass",
    }
)

# Unity 等渲染子窗口优先用于截屏
RENDER_WINDOW_CLASSES = frozenset({"UnityWndClass"})

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


@dataclass
class WindowRecord:
    hwnd: int
    title: str
    process_name: str
    class_name: str
    client_size: tuple[int, int]
    minimized: bool


@dataclass
class GameWindow:
    hwnd: int
    title: str
    process_name: str = ""
    class_name: str = ""

    @classmethod
    def find_by_titles(
        cls,
        title_substrings: list[str],
        *,
        title_exclude: list[str] | None = None,
        class_exclude: list[str] | None = None,
        process_names: list[str] | None = None,
        expected_size: tuple[int, int] | None = None,
        size_tolerance: int = 32,
        require_process: bool = False,
    ) -> GameWindow | None:
        selected, _ = cls._select_best(
            title_substrings,
            title_exclude=title_exclude,
            class_exclude=class_exclude,
            process_names=process_names,
            expected_size=expected_size,
            size_tolerance=size_tolerance,
            require_process=require_process,
        )
        return selected

    @classmethod
    def find_with_fallback(
        cls,
        title_substrings: list[str],
        *,
        title_exclude: list[str] | None = None,
        class_exclude: list[str] | None = None,
        process_names: list[str] | None = None,
        expected_size: tuple[int, int] | None = None,
        size_tolerance: int = 32,
    ) -> tuple[GameWindow | None, str]:
        """依次尝试：标题+进程 → 仅进程 → 仅标题。"""
        selected, _ = cls._select_best(
            title_substrings,
            title_exclude=title_exclude,
            class_exclude=class_exclude,
            process_names=process_names,
            expected_size=expected_size,
            size_tolerance=size_tolerance,
            require_process=bool(process_names),
            title_required=True,
            process_required=bool(process_names),
        )
        if selected is not None:
            return selected, "title+process"

        if process_names:
            selected, _ = cls._select_best(
                title_substrings,
                title_exclude=title_exclude,
                class_exclude=class_exclude,
                process_names=process_names,
                expected_size=expected_size,
                size_tolerance=size_tolerance,
                title_required=False,
                process_required=True,
            )
            if selected is not None:
                return selected, "process-only"

        selected, _ = cls._select_best(
            title_substrings,
            title_exclude=title_exclude,
            class_exclude=class_exclude,
            process_names=None,
            expected_size=expected_size,
            size_tolerance=size_tolerance,
            title_required=True,
            process_required=False,
        )
        if selected is not None:
            return selected, "title-only"

        return None, "none"

    @classmethod
    def list_candidates(
        cls,
        title_substrings: list[str],
        *,
        title_exclude: list[str] | None = None,
        class_exclude: list[str] | None = None,
        process_names: list[str] | None = None,
        expected_size: tuple[int, int] | None = None,
        size_tolerance: int = 32,
        limit: int = 12,
        verbose: bool = False,
    ) -> list[dict[str, object]]:
        selected, _ = cls._select_best(
            title_substrings,
            title_exclude=title_exclude,
            class_exclude=class_exclude,
            process_names=process_names,
            expected_size=expected_size,
            size_tolerance=size_tolerance,
            require_process=bool(process_names),
            title_required=True,
            process_required=bool(process_names),
        )
        selected_hwnd = selected.hwnd if selected is not None else None

        rows: list[tuple[float, dict[str, object]]] = []
        seen: set[int] = set()

        def add_row(record: WindowRecord, *, mode: str, score: float, note: str = "") -> None:
            if record.hwnd in seen:
                return
            seen.add(record.hwnd)
            w, h = record.client_size
            rows.append(
                (
                    score,
                    {
                        "hwnd": record.hwnd,
                        "title": record.title,
                        "process": record.process_name or "(unknown)",
                        "class": record.class_name,
                        "client_size": (w, h),
                        "score": score,
                        "mode": mode,
                        "note": note,
                        "selected": record.hwnd == selected_hwnd,
                        "minimized": record.minimized,
                    },
                )
            )

        for record in cls._iter_visible_windows(include_minimized=True):
            score = score_window_candidate(
                record.title,
                title_substrings,
                title_exclude or [],
                client_size=record.client_size,
                expected_size=expected_size,
                size_tolerance=size_tolerance,
                class_name=record.class_name,
                class_exclude=DEFAULT_CLASS_EXCLUDE | set(class_exclude or []),
                process_name=record.process_name,
                process_names={name.lower() for name in (process_names or []) if name},
                title_required=True,
                process_required=bool(process_names),
            )
            if score >= 0:
                add_row(record, mode="strict", score=score)

        if process_names:
            allowed = {name.lower() for name in process_names if name}
            for record in cls._iter_visible_windows(include_minimized=True):
                if record.process_name.lower() not in allowed:
                    continue
                score = score_window_candidate(
                    record.title,
                    title_substrings,
                    title_exclude or [],
                    client_size=record.client_size,
                    expected_size=expected_size,
                    size_tolerance=size_tolerance,
                    class_name=record.class_name,
                    class_exclude=DEFAULT_CLASS_EXCLUDE | set(class_exclude or []),
                    process_name=record.process_name,
                    process_names=allowed,
                    title_required=False,
                    process_required=True,
                )
                if score >= 0:
                    add_row(record, mode="process-only", score=score)

        for record in cls._iter_visible_windows(include_minimized=True):
            score = score_window_candidate(
                record.title,
                title_substrings,
                title_exclude or [],
                client_size=record.client_size,
                expected_size=expected_size,
                size_tolerance=size_tolerance,
                class_name=record.class_name,
                class_exclude=DEFAULT_CLASS_EXCLUDE | set(class_exclude or []),
                process_name=record.process_name,
                process_names=None,
                title_required=True,
                process_required=False,
            )
            if score >= 0:
                add_row(record, mode="title-only", score=score)

        if verbose:
            for record in cls._iter_visible_windows(include_minimized=True):
                if _title_looks_relevant(record.title, title_substrings):
                    reason = explain_rejection(
                        record,
                        title_substrings,
                        title_exclude or [],
                        class_exclude=class_exclude,
                        process_names=process_names,
                        expected_size=expected_size,
                        size_tolerance=size_tolerance,
                    )
                    add_row(
                        record,
                        mode="debug",
                        score=-1.0,
                        note=reason,
                    )

        if not rows and verbose:
            for record in cls._iter_visible_windows(include_minimized=True):
                w, h = record.client_size
                if w < 200 or h < 150:
                    continue
                add_row(
                    record,
                    mode="debug-large",
                    score=float(w * h),
                    note="large visible window",
                )

        rows.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in rows[:limit]]

    @classmethod
    def _select_best(
        cls,
        title_substrings: list[str],
        *,
        title_exclude: list[str] | None,
        class_exclude: list[str] | None,
        process_names: list[str] | None,
        expected_size: tuple[int, int] | None,
        size_tolerance: int,
        require_process: bool = False,
        title_required: bool = True,
        process_required: bool = False,
    ) -> tuple[GameWindow | None, list[tuple[WindowRecord, float]]]:
        allowed = {name.lower() for name in (process_names or []) if name}
        excluded_classes = DEFAULT_CLASS_EXCLUDE | set(class_exclude or [])
        ranked: list[tuple[WindowRecord, float]] = []

        for record in cls._iter_visible_windows(include_minimized=False):
            score = score_window_candidate(
                record.title,
                title_substrings,
                title_exclude or [],
                client_size=record.client_size,
                expected_size=expected_size,
                size_tolerance=size_tolerance,
                class_name=record.class_name,
                class_exclude=excluded_classes,
                process_name=record.process_name,
                process_names=allowed if process_names else None,
                title_required=title_required,
                process_required=process_required,
            )
            if score >= 0:
                ranked.append((record, score))

        if not ranked and require_process:
            for record in cls._iter_visible_windows(include_minimized=True):
                score = score_window_candidate(
                    record.title,
                    title_substrings,
                    title_exclude or [],
                    client_size=record.client_size,
                    expected_size=expected_size,
                    size_tolerance=size_tolerance,
                    class_name=record.class_name,
                    class_exclude=excluded_classes,
                    process_name=record.process_name,
                    process_names=allowed if process_names else None,
                    title_required=title_required,
                    process_required=process_required,
                )
                if score >= 0:
                    ranked.append((record, score))

        if not ranked:
            return None, ranked

        ranked.sort(key=lambda item: item[1], reverse=True)
        best = ranked[0][0]
        return (
            GameWindow(
                hwnd=best.hwnd,
                title=best.title,
                process_name=best.process_name,
                class_name=best.class_name,
            ),
            ranked,
        )

    @classmethod
    def _iter_visible_windows(cls, *, include_minimized: bool) -> list[WindowRecord]:
        records: list[WindowRecord] = []

        def callback(hwnd: int, _: object) -> bool:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            minimized = bool(win32gui.IsIconic(hwnd))
            if minimized and not include_minimized:
                return True
            title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            client_size = cls._client_size(hwnd)
            records.append(
                WindowRecord(
                    hwnd=hwnd,
                    title=title,
                    process_name=get_process_basename(hwnd),
                    class_name=class_name,
                    client_size=client_size,
                    minimized=minimized,
                )
            )
            return True

        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            pass
        return records

    @staticmethod
    def _client_size(hwnd: int) -> tuple[int, int]:
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        return right - left, bottom - top

    def capture_hwnd(self) -> int:
        """优先使用 Unity 等渲染子窗口截屏。"""
        cached = getattr(self, "_capture_hwnd_resolved", None)
        if cached is not None:
            return cached

        best_hwnd = self.hwnd
        best_area = 0
        parent_w, parent_h = self._client_size(self.hwnd)
        parent_area = max(parent_w * parent_h, 1)

        def visit(hwnd: int, _: object) -> bool:
            nonlocal best_hwnd, best_area
            if not win32gui.IsWindowVisible(hwnd):
                return True
            class_name = win32gui.GetClassName(hwnd)
            if class_name not in RENDER_WINDOW_CLASSES:
                return True
            w, h = self._client_size(hwnd)
            area = w * h
            if area > best_area and area >= parent_area * 0.5:
                best_area = area
                best_hwnd = hwnd
            return True

        try:
            win32gui.EnumChildWindows(self.hwnd, visit, None)
        except Exception:
            pass

        object.__setattr__(self, "_capture_hwnd_resolved", best_hwnd)
        return best_hwnd

    def focus(self) -> None:
        try:
            win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(self.hwnd)
        except Exception:
            pass

    def client_rect_screen(self) -> tuple[int, int, int, int]:
        """客户区在屏幕上的 (left, top, right, bottom)。"""
        hwnd = self.capture_hwnd()
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        pt = win32gui.ClientToScreen(hwnd, (left, top))
        width = right - left
        height = bottom - top
        return pt[0], pt[1], pt[0] + width, pt[1] + height

    def client_size(self) -> tuple[int, int]:
        """主窗口客户区尺寸（用于分辨率预检与日志）。"""
        return self._client_size(self.hwnd)

    def capture_client_size(self) -> tuple[int, int]:
        """实际截屏目标窗口的客户区尺寸。"""
        return self._client_size(self.capture_hwnd())

    def screen_to_client(self, x: int, y: int) -> tuple[int, int]:
        return win32gui.ScreenToClient(self.capture_hwnd(), (x, y))


def get_process_basename(hwnd: int) -> str:
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
    except Exception:
        return ""

    name = _process_basename_from_pid_query(pid)
    if name:
        return name

    try:
        handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_LIMITED_INFORMATION | win32con.PROCESS_VM_READ,
            False,
            pid,
        )
        try:
            path = win32process.GetModuleFileNameEx(handle, 0)
            return Path(path).name
        finally:
            win32api.CloseHandle(handle)
    except Exception:
        return ""


def _process_basename_from_pid_query(pid: int) -> str:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(buffer))
        ok = kernel32.QueryFullProcessImageNameW(
            handle,
            0,
            buffer,
            ctypes.byref(size),
        )
        if not ok:
            return ""
        return Path(buffer.value).name
    finally:
        kernel32.CloseHandle(handle)


def _title_looks_relevant(title: str, title_substrings: list[str]) -> bool:
    lowered = title.lower()
    hints = ("star", "rail", "崩坏", "星穹", "honkai", "mihoyo", "hoyoverse")
    if any(hint.lower() in lowered for hint in hints):
        return True
    return any(sub and sub in title for sub in title_substrings)


def explain_rejection(
    record: WindowRecord,
    title_substrings: list[str],
    title_exclude: list[str],
    *,
    class_exclude: list[str] | None,
    process_names: list[str] | None,
    expected_size: tuple[int, int] | None,
    size_tolerance: int,
) -> str:
    excluded_classes = DEFAULT_CLASS_EXCLUDE | set(class_exclude or [])
    if record.class_name in excluded_classes:
        return "excluded class"
    for excluded in title_exclude:
        if excluded and excluded in record.title:
            return f"title excluded: {excluded}"
    allowed = {name.lower() for name in (process_names or []) if name}
    if allowed and record.process_name and record.process_name.lower() not in allowed:
        return f"process mismatch: {record.process_name or '(unknown)'}"
    if not any(sub and sub in record.title for sub in title_substrings):
        return "title not matched"
    w, h = record.client_size
    if w < 320 or h < 240:
        return f"client too small: {w}x{h}"
    if expected_size is not None:
        ew, eh = expected_size
        if abs(w - ew) > size_tolerance or abs(h - eh) > size_tolerance:
            return f"resolution mismatch: {w}x{h} vs {ew}x{eh}"
    if record.minimized:
        return "minimized"
    return "unknown"


def score_window_candidate(
    title: str,
    title_substrings: list[str],
    title_exclude: list[str],
    *,
    client_size: tuple[int, int],
    expected_size: tuple[int, int] | None = None,
    size_tolerance: int = 32,
    class_name: str = "",
    class_exclude: set[str] | frozenset[str] | None = None,
    process_name: str = "",
    process_names: set[str] | frozenset[str] | None = None,
    title_required: bool = True,
    process_required: bool = False,
) -> float:
    """为候选窗口打分；返回 -1 表示排除。"""
    excluded_classes = class_exclude or set()
    if class_name in excluded_classes:
        return -1.0

    for excluded in title_exclude:
        if excluded and excluded in title:
            return -1.0

    allowed = process_names or set()
    if process_required:
        if not allowed:
            return -1.0
        if not process_name or process_name.lower() not in allowed:
            return -1.0
    elif allowed and process_name and process_name.lower() not in allowed:
        return -1.0

    match_index: int | None = None
    matched_len = 0
    for index, substring in enumerate(title_substrings):
        if substring and substring in title:
            if match_index is None:
                match_index = index
            matched_len = max(matched_len, len(substring))

    if title_required and match_index is None:
        return -1.0

    width, height = client_size
    if width < 320 or height < 240:
        return -1.0

    score = float(matched_len * 100)
    if match_index is not None:
        score += float((len(title_substrings) - match_index) * 10_000)

    if allowed and process_name and process_name.lower() in allowed:
        score += 50_000

    if expected_size is not None:
        expected_w, expected_h = expected_size
        dw = abs(width - expected_w)
        dh = abs(height - expected_h)
        if dw <= size_tolerance and dh <= size_tolerance:
            score += 10_000_000
        else:
            score -= float(dw + dh) * 5_000

    score += float(width * height) / 1000.0
    return score
