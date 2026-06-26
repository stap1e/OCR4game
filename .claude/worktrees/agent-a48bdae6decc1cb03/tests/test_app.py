import pytest

from ocr4game.app import main


def test_main_rejects_invalid_var() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--var", "badformat"])
    assert exc.value.code != 0


def test_main_list_games_exits_zero() -> None:
    assert main(["--list-games"]) == 0


def test_main_validate_offline() -> None:
    assert main(["--validate", "--game", "star_rail", "--task", "daily"]) == 0


def test_main_validate_strict_with_assets() -> None:
    assert main(["--validate", "--strict", "--game", "star_rail", "--task", "daily"]) == 0
