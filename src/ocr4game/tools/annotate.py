"""交互式截取游戏窗口 ROI，保存模板并写入 profile.yaml。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import yaml

from ocr4game.config import GameProfile, load_game_profile, load_global_config, load_yaml
from ocr4game.games.registry import get_plugin
from ocr4game.resources import game_assets_dir, game_profile_path
from ocr4game.runtime.binding import bind_runtime
from ocr4game.platform.window import GameWindow
from ocr4game.workflow.context import RunContext

# OpenCV 框选状态
_drawing = False
_start = (0, 0)
_end = (0, 0)
_frame = None
_clone = None


def _on_mouse(event, x, y, _flags, _param) -> None:
    global _drawing, _start, _end, _frame, _clone
    if event == cv2.EVENT_LBUTTONDOWN:
        _drawing = True
        _start = (x, y)
        _end = (x, y)
    elif event == cv2.EVENT_MOUSEMOVE and _drawing:
        _end = (x, y)
        _frame = _clone.copy()
        cv2.rectangle(_frame, _start, _end, (0, 255, 0), 2)
    elif event == cv2.EVENT_LBUTTONUP:
        _drawing = False
        _end = (x, y)


def _relative_roi(
    x0: int, y0: int, x1: int, y1: int, w: int, h: int
) -> list[float]:
    x0 = max(0, min(x0, w))
    x1 = max(0, min(x1, w))
    y0 = max(0, min(y0, h))
    y1 = max(0, min(y1, h))
    left, top = min(x0, x1), min(y0, y1)
    right, bottom = max(x0, x1), max(y0, y1)
    return [
        round(left / w, 4),
        round(top / h, 4),
        round(right / w, 4),
        round(bottom / h, 4),
    ]


def _update_profile_anchor(
    profile_path: Path,
    anchor_name: str,
    image_rel: str,
    roi: list[float],
    threshold: float = 0.88,
) -> None:
    data = load_yaml(profile_path)
    anchors = data.setdefault("anchors", {})
    anchors[anchor_name] = {
        "type": "template",
        "image": image_rel,
        "threshold": threshold,
        "roi": roi,
    }
    profile = GameProfile.model_validate(data)
    with profile_path.open("w", encoding="utf-8") as f:
        yaml.dump(profile.model_dump(mode="python"), f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="框选 UI 并保存为模板")
    parser.add_argument("--game", default="star_rail")
    parser.add_argument("--name", help="锚点名称，如 claim_button")
    parser.add_argument("--threshold", type=float, default=0.88)
    parser.add_argument(
        "--list-windows",
        action="store_true",
        help="列出匹配到的候选窗口并退出（排查误绑）",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="与 --list-windows 联用，显示近匹配窗口与排除原因",
    )
    args = parser.parse_args(argv)

    if not args.list_windows and not args.name:
        parser.error("the following arguments are required: --name（使用 --list-windows 时可省略）")

    global_cfg = load_global_config()
    profile = load_game_profile(args.game)
    window_cfg = profile.window
    resolution = profile.resolution

    if args.list_windows:
        rows = GameWindow.list_candidates(
            window_cfg.title_contains,
            title_exclude=window_cfg.title_exclude,
            class_exclude=window_cfg.class_exclude,
            process_names=window_cfg.process_names,
            expected_size=(resolution.width, resolution.height),
            size_tolerance=resolution.tolerance,
            verbose=args.verbose,
        )
        if not rows:
            print("未找到候选窗口。")
            print("请确认：")
            print("  1. 游戏已窗口化启动（不要最小化到任务栏）")
            print("  2. 分辨率与 profile.yaml 中 resolution 一致")
            print("  3. 运行诊断：ocr4game-annotate --game star_rail --list-windows --verbose")
            print("  4. 若 verbose 里 process 不是 StarRail.exe，将其填入 profile.yaml → process_names")
            return 1
        for row in rows:
            mark = " <-- 已选" if row.get("selected") else ""
            w, h = row["client_size"]  # type: ignore[index]
            note = row.get("note")
            note_text = f" note={note!r}" if note else ""
            mode = row.get("mode", "")
            print(
                f"[{mode}] score={row['score']:.0f} hwnd={row['hwnd']} "
                f"size={w}x{h} process={row['process']} class={row['class']} "
                f"title={row['title']!r}{note_text}{mark}"
            )
        return 0

    plugin = get_plugin(profile)
    ctx = RunContext(profile=profile, global_cfg=global_cfg)
    if not bind_runtime(ctx) or not plugin.preflight(ctx):
        print("未找到游戏窗口，请先窗口化启动游戏。", file=sys.stderr)
        return 1

    print("已绑定游戏窗口，正在截取画面（请勿让终端遮挡游戏）…", flush=True)
    frame = ctx.grab_frame()
    h, w = frame.shape[:2]
    global _frame, _clone
    _clone = frame.copy()
    _frame = frame.copy()

    win = "ocr4game-annotate — 拖拽框选，Enter 确认，Esc 取消"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(win, _on_mouse)

    while True:
        cv2.imshow(win, _frame)
        key = cv2.waitKey(20) & 0xFF
        if key == 27:
            cv2.destroyAllWindows()
            return 0
        if key in (13, 10):
            break

    cv2.destroyAllWindows()
    x0, y0 = _start
    x1, y1 = _end
    if abs(x1 - x0) < 4 or abs(y1 - y0) < 4:
        print("选区过小", file=sys.stderr)
        return 1

    left, top = min(x0, x1), min(y0, y1)
    right, bottom = max(x0, x1), max(y0, y1)
    left = max(0, min(left, w))
    right = max(0, min(right, w))
    top = max(0, min(top, h))
    bottom = max(0, min(bottom, h))
    crop = _clone[top:bottom, left:right]

    ui_dir = game_assets_dir(profile) / "ui"
    ui_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{args.name}.png"
    out_path = ui_dir / filename
    if not cv2.imwrite(str(out_path), crop):
        print(f"保存模板失败: {out_path}", file=sys.stderr)
        return 1

    roi = _relative_roi(x0, y0, x1, y1, w, h)
    image_rel = f"ui/{filename}"
    profile_path = game_profile_path(args.game)
    _update_profile_anchor(profile_path, args.name, image_rel, roi, args.threshold)

    print(f"已保存模板: {out_path}")
    print(f"已更新锚点: {args.name} -> {image_rel} roi={roi}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
