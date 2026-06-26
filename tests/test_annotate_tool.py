from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest
import yaml

from ocr4game.tools import annotate


class _Plugin:
    def preflight(self, _ctx) -> bool:
        return True


class _FakeContext:
    frames: list[np.ndarray] = []
    instances: list[_FakeContext] = []

    def __init__(self, **_kwargs) -> None:
        self.grab_count = 0
        self.instances.append(self)

    def grab_frame(self) -> np.ndarray:
        frame = self.frames[min(self.grab_count, len(self.frames) - 1)]
        self.grab_count += 1
        return frame.copy()


@pytest.fixture(autouse=True)
def reset_state() -> None:
    annotate._reset_selection(np.zeros((8, 8, 3), dtype=np.uint8))
    _FakeContext.frames = []
    _FakeContext.instances = []


@pytest.fixture
def annotate_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        Path("configs/games/star_rail/profile.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assets_dir = tmp_path / "assets"

    monkeypatch.setattr(annotate, "RunContext", _FakeContext)
    monkeypatch.setattr(annotate, "bind_runtime", lambda _ctx: True)
    monkeypatch.setattr(annotate, "get_plugin", lambda _profile: _Plugin())
    monkeypatch.setattr(annotate, "game_assets_dir", lambda _profile: assets_dir)
    monkeypatch.setattr(annotate, "game_profile_path", lambda _game: profile_path)

    return profile_path, assets_dir


def _install_cv2_ui(
    monkeypatch: pytest.MonkeyPatch,
    events_by_tick: list[list[tuple[int, int, int]]],
    keys: list[int],
):
    callback = None
    saved: dict[str, object] = {"images": []}

    def set_mouse_callback(_win: str, cb) -> None:
        nonlocal callback
        callback = cb

    def wait_key(_delay: int) -> int:
        tick = len(saved["images"]) - 1
        for event, x, y in events_by_tick[tick] if tick < len(events_by_tick) else []:
            assert callback is not None
            callback(event, x, y, None, None)
        return keys.pop(0)

    def imwrite(path: str, image: np.ndarray) -> bool:
        saved["path"] = path
        saved["crop"] = image.copy()
        return True

    monkeypatch.setattr(annotate.cv2, "namedWindow", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(annotate.cv2, "setMouseCallback", set_mouse_callback)
    monkeypatch.setattr(annotate.cv2, "imshow", lambda _win, image: saved["images"].append(image.copy()))
    monkeypatch.setattr(annotate.cv2, "waitKey", wait_key)
    monkeypatch.setattr(annotate.cv2, "destroyAllWindows", lambda: saved.setdefault("destroyed", True))
    monkeypatch.setattr(annotate.cv2, "imwrite", imwrite)
    return saved


def test_annotate_esc_cancels_without_saving(
    monkeypatch: pytest.MonkeyPatch,
    annotate_runtime,
) -> None:
    _FakeContext.frames = [np.zeros((20, 20, 3), dtype=np.uint8)]
    saved = _install_cv2_ui(monkeypatch, [[]], [27])

    code = annotate.main(["--game", "star_rail", "--name", "claim_button"])

    assert code == 0
    assert "path" not in saved
    assert _FakeContext.instances[0].grab_count == 1


def test_annotate_recaptures_with_r_and_uses_new_frame(
    monkeypatch: pytest.MonkeyPatch,
    annotate_runtime,
) -> None:
    first = np.zeros((20, 20, 3), dtype=np.uint8)
    second = np.full((20, 20, 3), 9, dtype=np.uint8)
    _FakeContext.frames = [first, second]
    saved = _install_cv2_ui(
        monkeypatch,
        [
            [
                (cv2.EVENT_LBUTTONDOWN, 1, 1),
                (cv2.EVENT_LBUTTONUP, 8, 8),
            ],
            [
                (cv2.EVENT_LBUTTONDOWN, 2, 3),
                (cv2.EVENT_LBUTTONUP, 10, 12),
            ],
        ],
        [ord("r"), 13],
    )

    code = annotate.main(["--game", "star_rail", "--name", "claim_button"])

    assert code == 0
    assert _FakeContext.instances[0].grab_count == 2
    crop = saved["crop"]
    assert isinstance(crop, np.ndarray)
    assert crop.shape == (9, 8, 3)
    assert np.all(crop == 9)


def test_annotate_tiny_selection_keeps_session_until_valid(
    monkeypatch: pytest.MonkeyPatch,
    annotate_runtime,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _FakeContext.frames = [np.full((20, 20, 3), 5, dtype=np.uint8)]
    saved = _install_cv2_ui(
        monkeypatch,
        [
            [
                (cv2.EVENT_LBUTTONDOWN, 1, 1),
                (cv2.EVENT_LBUTTONUP, 2, 2),
            ],
            [
                (cv2.EVENT_LBUTTONDOWN, 4, 5),
                (cv2.EVENT_LBUTTONUP, 12, 14),
            ],
        ],
        [13, 13],
    )

    code = annotate.main(["--game", "star_rail", "--name", "claim_button"])

    assert code == 0
    assert "选区过小" in capsys.readouterr().err
    crop = saved["crop"]
    assert isinstance(crop, np.ndarray)
    assert crop.shape == (9, 8, 3)


def test_annotate_valid_selection_updates_profile(
    monkeypatch: pytest.MonkeyPatch,
    annotate_runtime,
) -> None:
    profile_path, _assets_dir = annotate_runtime
    _FakeContext.frames = [np.full((20, 40, 3), 7, dtype=np.uint8)]
    saved = _install_cv2_ui(
        monkeypatch,
        [
            [
                (cv2.EVENT_LBUTTONDOWN, 4, 6),
                (cv2.EVENT_LBUTTONUP, 20, 16),
            ]
        ],
        [13],
    )

    code = annotate.main(["--game", "star_rail", "--name", "claim_button", "--threshold", "0.77"])

    assert code == 0
    assert Path(str(saved["path"])).parts[-3:] == ("assets", "ui", "claim_button.png")
    crop = saved["crop"]
    assert isinstance(crop, np.ndarray)
    assert crop.shape == (10, 16, 3)

    data = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    anchor = data["anchors"]["claim_button"]
    assert anchor["type"] == "template"
    assert anchor["image"] == "ui/claim_button.png"
    assert anchor["threshold"] == 0.77
    assert anchor["roi"] == [0.1, 0.3, 0.5, 0.8]


def test_selection_bounds_clamps_reversed_coordinates() -> None:
    assert annotate._selection_bounds(12, 15, -3, 2, 10, 8) == (0, 2, 10, 8)
    assert annotate._relative_roi(12, 15, -3, 2, 10, 8) == [0.0, 0.25, 1.0, 1.0]
