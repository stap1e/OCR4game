"""生成星穹铁道合成 fixture 图（运行: python tests/fixtures/generate_star_rail.py）。"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "src"))

import cv2
import numpy as np
import yaml

FIXTURES = Path(__file__).resolve().parent / "star_rail"
FRAMES = FIXTURES / "frames"
TEMPLATES = FIXTURES / "templates"

# 2048×1152 的 1/4，测试更快、PNG 更小
W, H = 512, 288


def _blank_frame(*, bordered: bool = True) -> np.ndarray:
    frame = np.full((H, W, 3), (28, 32, 40), dtype=np.uint8)
    if bordered:
        cv2.rectangle(frame, (0, 0), (W - 1, H - 1), (55, 60, 72), 1)
    return frame


def _draw_button(
    frame: np.ndarray,
    cx: int,
    cy: int,
    *,
    w: int = 72,
    h: int = 28,
    fill: tuple[int, int, int] = (90, 140, 220),
) -> tuple[np.ndarray, np.ndarray]:
    x0, y0 = cx - w // 2, cy - h // 2
    x1, y1 = x0 + w, y0 + h
    cv2.rectangle(frame, (x0, y0), (x1, y1), fill, -1)
    cv2.rectangle(frame, (x0, y0), (x1, y1), (200, 210, 230), 1)
    template = frame[y0:y1, x0:x1].copy()
    return frame, template


def _save(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), image)


def main() -> None:
    FRAMES.mkdir(parents=True, exist_ok=True)
    TEMPLATES.mkdir(parents=True, exist_ok=True)

    # --- main_menu: 顶部条带标记 ---
    main_menu = _blank_frame()
    cv2.rectangle(main_menu, (8, 6), (88, 28), (180, 160, 90), -1)
    cv2.rectangle(main_menu, (8, 6), (88, 28), (240, 220, 160), 1)
    main_menu_tpl = main_menu[6:28, 8:88].copy()
    _save(FRAMES / "main_menu.png", main_menu)
    _save(TEMPLATES / "main_menu_marker.png", main_menu_tpl)

    # --- daily_panel: 日常面板 + 领取按钮 ---
    daily_panel = _blank_frame()
    cv2.rectangle(daily_panel, (0, 0), (W - 1, int(H * 0.15)), (45, 50, 62), -1)
    cv2.putText(
        daily_panel,
        "Daily",
        (12, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (210, 210, 220),
        1,
        cv2.LINE_AA,
    )
    daily_panel_marker_tpl = daily_panel[0 : int(H * 0.15), 0 : int(W * 0.4)].copy()
    daily_panel, claim_tpl = _draw_button(daily_panel, W // 2, int(H * 0.72), fill=(100, 190, 120))
    _save(FRAMES / "daily_panel.png", daily_panel)
    _save(TEMPLATES / "daily_panel_marker.png", daily_panel_marker_tpl)
    _save(TEMPLATES / "claim_button.png", claim_tpl)

    # --- guide_screen: 左侧指南入口 ---
    guide_screen = _blank_frame()
    guide_screen, guide_tpl = _draw_button(
        guide_screen, 48, 52, w=56, h=24, fill=(150, 110, 210)
    )
    _save(FRAMES / "guide_screen.png", guide_screen)
    _save(TEMPLATES / "guide_entrance.png", guide_tpl)

    # --- sweep_dialog: 扫荡确认 ---
    sweep_dialog = _blank_frame()
    cv2.rectangle(
        sweep_dialog,
        (int(W * 0.2), int(H * 0.25)),
        (int(W * 0.8), int(H * 0.85)),
        (38, 42, 52),
        -1,
    )
    sweep_dialog, sweep_tpl = _draw_button(
        sweep_dialog, int(W * 0.72), int(H * 0.78), fill=(210, 130, 80)
    )
    sweep_dialog, confirm_tpl = _draw_button(
        sweep_dialog, W // 2, int(H * 0.68), fill=(80, 170, 210)
    )
    _save(FRAMES / "sweep_dialog.png", sweep_dialog)
    _save(TEMPLATES / "sweep_button.png", sweep_tpl)
    _save(TEMPLATES / "confirm_button.png", confirm_tpl)

    # --- dialog: 右上角关闭 ---
    dialog = _blank_frame()
    cv2.rectangle(
        dialog,
        (int(W * 0.15), int(H * 0.12)),
        (int(W * 0.85), int(H * 0.88)),
        (50, 54, 66),
        -1,
    )
    close_x0, close_y0 = int(W * 0.78), int(H * 0.14)
    close_x1, close_y1 = int(W * 0.94), int(H * 0.28)
    cv2.rectangle(dialog, (close_x0, close_y0), (close_x1, close_y1), (220, 70, 70), -1)
    cv2.rectangle(dialog, (close_x0, close_y0), (close_x1, close_y1), (255, 180, 180), 2)
    close_tpl = dialog[close_y0:close_y1, close_x0:close_x1].copy()
    _save(FRAMES / "reward_dialog.png", dialog)
    _save(TEMPLATES / "dialog_close.png", close_tpl)

    # --- empty: 负样本（纯色，无 UI 元素） ---
    _save(FRAMES / "empty.png", _blank_frame(bordered=False))

    no_main = _blank_frame(bordered=False)
    cv2.rectangle(no_main, (0, 0), (W - 1, int(H * 0.12)), (180, 50, 50), -1)
    _save(FRAMES / "no_main_menu.png", no_main)

    manifest = {
        "game_id": "star_rail",
        "frame_size": [W, H],
        "production_resolution": [2048, 1152],
        "cases": [
            {
                "id": "main_menu_marker_hit",
                "anchor": "main_menu_marker",
                "frame": "frames/main_menu.png",
                "template": "templates/main_menu_marker.png",
                "roi": [0.0, 0.0, 1.0, 0.12],
                "threshold": 0.85,
                "expect_found": True,
            },
            {
                "id": "main_menu_marker_miss",
                "anchor": "main_menu_marker",
                "frame": "frames/no_main_menu.png",
                "template": "templates/main_menu_marker.png",
                "roi": [0.0, 0.0, 1.0, 0.12],
                "threshold": 0.85,
                "expect_found": False,
            },
            {
                "id": "claim_button_hit",
                "anchor": "claim_button",
                "frame": "frames/daily_panel.png",
                "template": "templates/claim_button.png",
                "roi": [0.3, 0.5, 0.7, 0.95],
                "threshold": 0.88,
                "expect_found": True,
            },
            {
                "id": "daily_panel_marker_hit",
                "anchor": "daily_panel_marker",
                "frame": "frames/daily_panel.png",
                "template": "templates/daily_panel_marker.png",
                "roi": [0.0, 0.0, 1.0, 0.15],
                "threshold": 0.85,
                "expect_found": True,
            },
            {
                "id": "claim_button_miss",
                "anchor": "claim_button",
                "frame": "frames/main_menu.png",
                "template": "templates/claim_button.png",
                "roi": [0.3, 0.5, 0.7, 0.95],
                "threshold": 0.88,
                "expect_found": False,
            },
            {
                "id": "guide_entrance_hit",
                "anchor": "guide_entrance",
                "frame": "frames/guide_screen.png",
                "template": "templates/guide_entrance.png",
                "roi": [0.0, 0.0, 0.15, 0.25],
                "threshold": 0.85,
                "expect_found": True,
            },
            {
                "id": "sweep_button_hit",
                "anchor": "sweep_button",
                "frame": "frames/sweep_dialog.png",
                "template": "templates/sweep_button.png",
                "roi": [0.55, 0.6, 0.95, 0.95],
                "threshold": 0.88,
                "expect_found": True,
            },
            {
                "id": "confirm_button_hit",
                "anchor": "confirm_button",
                "frame": "frames/sweep_dialog.png",
                "template": "templates/confirm_button.png",
                "roi": [0.35, 0.55, 0.65, 0.85],
                "threshold": 0.88,
                "expect_found": True,
            },
            {
                "id": "dialog_close_hit",
                "anchor": "dialog_close",
                "frame": "frames/reward_dialog.png",
                "template": "templates/dialog_close.png",
                "roi": [0.72, 0.08, 0.98, 0.32],
                "threshold": 0.85,
                "expect_found": True,
            },
        ],
    }

    manifest_path = FIXTURES / "manifest.yaml"
    with manifest_path.open("w", encoding="utf-8") as f:
        yaml.dump(manifest, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    print(f"Wrote fixtures under {FIXTURES}")

    from ocr4game.config import load_game_profile
    from ocr4game.tools.asset_sync import sync_templates_to_assets

    profile = load_game_profile("star_rail")
    copied = sync_templates_to_assets(profile, source_dir=TEMPLATES)
    print(f"Synced {len(copied)} templates -> assets/ui/")


if __name__ == "__main__":
    main()
