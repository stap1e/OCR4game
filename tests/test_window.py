"""窗口候选打分逻辑测试。"""

from ocr4game.platform.window import score_window_candidate


def test_score_prefers_resolution_match() -> None:
    low = score_window_candidate(
        "崩坏：星穹铁道",
        ["崩坏：星穹铁道"],
        [],
        client_size=(1280, 720),
        expected_size=(1280, 720),
        size_tolerance=16,
    )
    high = score_window_candidate(
        "崩坏：星穹铁道",
        ["崩坏：星穹铁道"],
        [],
        client_size=(2048, 1152),
        expected_size=(1280, 720),
        size_tolerance=16,
    )
    assert low > high


def test_score_excludes_title_substrings() -> None:
    score = score_window_candidate(
        "OCR4game - Cursor",
        ["Star Rail"],
        ["Cursor"],
        client_size=(1280, 720),
    )
    assert score < 0


def test_score_prefers_longer_title_match() -> None:
    specific = score_window_candidate(
        "崩坏：星穹铁道",
        ["崩坏：星穹铁道", "Star Rail"],
        [],
        client_size=(1280, 720),
    )
    generic = score_window_candidate(
        "Some Star Rail Guide",
        ["崩坏：星穹铁道", "Star Rail"],
        [],
        client_size=(1280, 720),
    )
    assert specific > generic


def test_score_requires_process_when_configured() -> None:
    allowed = score_window_candidate(
        "崩坏：星穹铁道",
        ["崩坏：星穹铁道"],
        [],
        client_size=(1280, 720),
        process_name="StarRail.exe",
        process_names={"starrail.exe"},
        process_required=True,
    )
    blocked = score_window_candidate(
        "崩坏：星穹铁道",
        ["崩坏：星穹铁道"],
        [],
        client_size=(1280, 720),
        process_name="powershell.exe",
        process_names={"starrail.exe"},
        process_required=True,
    )
    assert allowed >= 0
    assert blocked < 0


def test_score_process_only_without_title() -> None:
    score = score_window_candidate(
        "",
        ["崩坏：星穹铁道"],
        [],
        client_size=(1280, 720),
        process_name="StarRail.exe",
        process_names={"starrail.exe"},
        title_required=False,
        process_required=True,
    )
    assert score >= 0


def test_score_excludes_console_class() -> None:
    score = score_window_candidate(
        "崩坏：星穹铁道",
        ["崩坏：星穹铁道"],
        [],
        client_size=(1280, 720),
        class_name="ConsoleWindowClass",
        class_exclude={"ConsoleWindowClass"},
    )
    assert score < 0
