"""从本地目录批量导入真实截图到 assets/ui 与 tests/fixtures。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ocr4game.config import load_game_profile
from ocr4game.tools.asset_sync import import_screenshots


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="导入真实截图（ui/*.png → assets/ui；frames/*.png → tests/fixtures）"
    )
    parser.add_argument("--game", default="star_rail")
    parser.add_argument(
        "--from-dir",
        type=Path,
        required=True,
        help="源目录，含 ui/ 与可选 frames/ 子目录",
    )
    parser.add_argument(
        "--no-fixtures",
        action="store_true",
        help="不同步到 tests/fixtures",
    )
    args = parser.parse_args(argv)

    if not args.from_dir.is_dir():
        print(f"目录不存在: {args.from_dir}", file=sys.stderr)
        return 1

    profile = load_game_profile(args.game)
    assets, fixtures, frames = import_screenshots(
        profile,
        args.from_dir,
        sync_fixtures=not args.no_fixtures,
    )

    if not assets and not fixtures and not frames:
        print("未找到可导入的 PNG（请按 ui/<anchor>.png 命名）", file=sys.stderr)
        return 1

    for path in assets:
        print(f"assets: {path}")
    for path in fixtures:
        print(f"fixtures/templates: {path}")
    for path in frames:
        print(f"fixtures/frames: {path}")
    print(f"完成：{len(assets)} 个 assets 模板，{len(fixtures)} 个 fixture 模板，{len(frames)} 个帧图")
    return 0


if __name__ == "__main__":
    sys.exit(main())
