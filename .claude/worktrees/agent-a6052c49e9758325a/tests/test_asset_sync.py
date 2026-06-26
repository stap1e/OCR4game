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


def test_import_screenshots_preserves_nested_paths_and_frame_extensions(tmp_path, monkeypatch) -> None:
    from ocr4game.config import GameProfile, PathsConfig, TemplateAnchorConfig

    profile = GameProfile(
        game_id="test_game",
        paths=PathsConfig(assets="assets"),
        anchors={
            "btn": TemplateAnchorConfig(image="ui/buttons/btn.png", threshold=0.85),
        },
    )
    src = tmp_path / "shots"
    (src / "ui" / "ui" / "buttons").mkdir(parents=True)
    (src / "ui" / "ui" / "buttons" / "btn.png").write_bytes(b"png")
    (src / "frames" / "nested").mkdir(parents=True)
    (src / "frames" / "nested" / "screen.jpg").write_bytes(b"jpg")

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
    assert assets == [tmp_path / "assets" / "ui" / "buttons" / "btn.png"]
    assert fixtures == [tmp_path / "fixtures" / "templates" / "ui" / "buttons" / "btn.png"]
    assert frames == [tmp_path / "fixtures" / "frames" / "nested" / "screen.jpg"]
