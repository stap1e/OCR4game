"""在 fixtures 模板与 assets/ui 之间同步 PNG。"""

from __future__ import annotations

import shutil
from pathlib import Path

from ocr4game.config import GameProfile, TemplateAnchorConfig, load_game_profile
from ocr4game.resources import game_assets_dir, repo_root

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def fixture_templates_dir(game_id: str = "star_rail") -> Path:
    return repo_root() / "tests" / "fixtures" / game_id / "templates"


def fixture_frames_dir(game_id: str = "star_rail") -> Path:
    return repo_root() / "tests" / "fixtures" / game_id / "frames"


def sync_templates_to_assets(profile: GameProfile, *, source_dir: Path | None = None) -> list[Path]:
    """将模板图片复制到 configs/games/<id>/assets/。"""
    src_root = source_dir or fixture_templates_dir(profile.game_id)
    assets_dir = game_assets_dir(profile)
    assets_dir.mkdir(parents=True, exist_ok=True)

    copied: list[Path] = []
    for name, anchor in profile.anchors.items():
        if not isinstance(anchor, TemplateAnchorConfig):
            continue
        image_rel = Path(anchor.image)
        src = src_root / image_rel
        if not src.is_file():
            src = src_root / image_rel.name
        if not src.is_file():
            src = src_root.parent / image_rel
        if not src.is_file():
            continue
        dst = assets_dir / image_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(dst)
    return copied


def import_screenshots(
    profile: GameProfile,
    source_dir: Path,
    *,
    sync_fixtures: bool = True,
) -> tuple[list[Path], list[Path], list[Path]]:
    """从用户目录导入 ui/ 与 frames/ 到 assets 与 tests/fixtures。"""
    ui_src = source_dir / "ui"
    frames_src = source_dir / "frames"
    if not ui_src.is_dir() and not frames_src.is_dir():
        # 允许扁平目录：*.png 按文件名匹配锚点
        ui_src = source_dir

    assets_dir = game_assets_dir(profile)
    assets_dir.mkdir(parents=True, exist_ok=True)
    fixture_tpl = fixture_templates_dir(profile.game_id)
    fixture_frm = fixture_frames_dir(profile.game_id)
    fixture_tpl.mkdir(parents=True, exist_ok=True)
    fixture_frm.mkdir(parents=True, exist_ok=True)

    imported_assets: list[Path] = []
    imported_fixtures: list[Path] = []
    imported_frames: list[Path] = []

    if ui_src.is_dir():
        for name, anchor in profile.anchors.items():
            if not isinstance(anchor, TemplateAnchorConfig):
                continue
            image_rel = Path(anchor.image)
            candidates = [ui_src / image_rel, ui_src / image_rel.name, source_dir / image_rel]
            src = next((p for p in candidates if p.is_file()), None)
            if src is None:
                continue
            dst_asset = assets_dir / image_rel
            dst_asset.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst_asset)
            imported_assets.append(dst_asset)
            if sync_fixtures:
                dst_fixture = fixture_tpl / image_rel
                dst_fixture.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst_fixture)
                imported_fixtures.append(dst_fixture)

    if frames_src.is_dir():
        for image in frames_src.rglob("*"):
            if not image.is_file() or image.suffix.lower() not in _IMAGE_EXTENSIONS:
                continue
            dst = fixture_frm / image.relative_to(frames_src)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image, dst)
            imported_frames.append(dst)

    return imported_assets, imported_fixtures, imported_frames
