"""交互式截取游戏窗口 ROI，保存模板并写入 profile.yaml。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import yaml

from ocr4game.config import GameProfile, game_config_dir, load_yaml
from ocr4game.games.registry import get_plugin
from ocr4game.workflow.context import RunContext
from ocr4game.config import GlobalConfig

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
    with profile_path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="框选 UI 并保存为模板")
    parser.add_argument("--game", default="star_rail")
    parser.add_argument("--name", required=True, help="锚点名称，如 claim_button")
    parser.add_argument("--threshold", type=float, default=0.88)
    args = parser.parse_args(argv)

    global_cfg = GlobalConfig.load()
    profile = GameProfile.load(args.game)
    plugin = get_plugin(profile)
    ctx = RunContext(profile=profile, global_cfg=global_cfg)
    if not plugin.preflight(ctx):
        print("未找到游戏窗口，请先窗口化启动游戏。", file=sys.stderr)
        return 1

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
    crop = _clone[top:bottom, left:right]

    ui_dir = profile.assets_dir() / "ui"
    ui_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{args.name}.png"
    out_path = ui_dir / filename
    cv2.imwrite(str(out_path), crop)

    roi = _relative_roi(x0, y0, x1, y1, w, h)
    image_rel = f"ui/{filename}"
    profile_path = game_config_dir(args.game) / "profile.yaml"
    _update_profile_anchor(profile_path, args.name, image_rel, roi, args.threshold)

    print(f"已保存模板: {out_path}")
    print(f"已更新锚点: {args.name} -> {image_rel} roi={roi}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
