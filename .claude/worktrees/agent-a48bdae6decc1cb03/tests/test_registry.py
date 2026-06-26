from ocr4game.games.registry import discover_configured_games, list_registered_games


def test_star_rail_is_registered_and_configured() -> None:
    assert "star_rail" in list_registered_games()
    assert "star_rail" in discover_configured_games()


def test_template_scaffold_is_not_discovered() -> None:
    configured = discover_configured_games()
    assert "_template" not in configured
    assert "my_game" not in configured
