import shutil
from pathlib import Path

from ocr4game.tools.asset_sync import import_screenshots, sync_templates_to_assets


def test_sync_templates_to_assets(tmp_path, monkeypatch) -> None:
    from ocr4game.config import GameProfile, PathsConfig, TemplateAnchorConfig

    profile = GameProfile(
        game_id="test_game",
        paths=PathsConfig(assets="assets"),
        anchors={
            "btn": TemplateAnchorConfig(image="ui/btn.png", threshold=0.85),
        },
    )
    src = tmp_path / "templates"
    src.mkdir()
    png = src / "btn.png"
    png.write_bytes(b"png")

    assets = tmp_path / "assets" / "ui"
    monkeypatch.setattr(
        "ocr4game.tools.asset_sync.game_assets_dir",
        lambda _p: tmp_path / "assets",
    )

    copied = sync_templates_to_assets(profile, source_dir=src)
    assert copied == [assets / "btn.png"]
    assert (assets / "btn.png").is_file()


def test_import_screenshots_flat_dir(tmp_path, monkeypatch) -> None:
    from ocr4game.config import GameProfile, PathsConfig, TemplateAnchorConfig

    profile = GameProfile(
        game_id="test_game",
        paths=PathsConfig(assets="assets"),
        anchors={
            "btn": TemplateAnchorConfig(image="ui/btn.png", threshold=0.85),
        },
    )
    src = tmp_path / "shots"
    src.mkdir()
    (src / "btn.png").write_bytes(b"png")

    monkeypatch.setattr(
        "ocr4game.tools.asset_sync.game_assets_dir",
        lambda _p: tmp_path / "assets",
    )
    monkeypatch.setattr(
        "ocr4game.tools.asset_sync.fixture_templates_dir",
        lambda _gid: tmp_path / "fixtures" / "templates",
    )
    monkeypatch.setattr(
        "ocr4game.tools.asset_sync.fixture_frames_dir",
        lambda _gid: tmp_path / "fixtures" / "frames",
    )

    assets, fixtures, frames = import_screenshots(profile, src)
    assert len(assets) == 1
    assert len(fixtures) == 1
    assert not frames
