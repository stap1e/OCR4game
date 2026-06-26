import pytest

from ocr4game.config import load_game_profile
from ocr4game.workflow.conditions import (
    ConditionError,
    evaluate_condition,
    validate_condition_syntax,
)
from ocr4game.workflow.context import RunContext


class DummyPerception:
    def __init__(self, visible: set[str]) -> None:
        self.visible = visible

    def evaluate_anchor(self, _frame, anchor_name: str):
        from types import SimpleNamespace

        return SimpleNamespace(found=anchor_name in self.visible, kind="template", confidence=0.9)


@pytest.fixture
def ctx() -> RunContext:
    profile = load_game_profile("star_rail")
    from ocr4game.config import load_global_config

    run = RunContext(profile=profile, global_cfg=load_global_config())
    run.vars = {"sweep_times": 2, "enable_sweep": True}
    run.capture = object()
    run.perception = DummyPerception({"claim_button", "main_menu_marker"})
    run.grab_frame = lambda: None  # type: ignore[method-assign]
    return run


def test_anchor_visible_and_missing(ctx: RunContext) -> None:
    assert evaluate_condition({"anchor_visible": "claim_button"}, ctx)
    assert not evaluate_condition({"anchor_visible": "sweep_button"}, ctx)
    assert evaluate_condition({"anchor_missing": "sweep_button"}, ctx)


def test_var_comparisons(ctx: RunContext) -> None:
    assert evaluate_condition({"var_gt": {"sweep_times": 1}}, ctx)
    assert evaluate_condition({"var_eq": {"enable_sweep": True}}, ctx)
    assert not evaluate_condition({"var_eq": {"sweep_times": 3}}, ctx)


def test_all_any_not(ctx: RunContext) -> None:
    assert evaluate_condition(
        {"all": [{"anchor_visible": "claim_button"}, {"var_gt": {"sweep_times": 0}}]},
        ctx,
    )
    assert evaluate_condition(
        {"any": [{"anchor_visible": "missing"}, {"anchor_visible": "claim_button"}]},
        ctx,
    )
    assert not evaluate_condition({"not": {"anchor_visible": "claim_button"}}, ctx)


def test_validate_condition_syntax() -> None:
    profile = load_game_profile("star_rail")
    errors = validate_condition_syntax(
        {"anchor_visible": "claim_button"},
        profile=profile,
        path="when",
    )
    assert not errors

    errors = validate_condition_syntax(
        {"anchor_visible": "not_exists"},
        profile=profile,
        path="when",
    )
    assert errors


def test_invalid_condition_raises(ctx: RunContext) -> None:
    with pytest.raises(ConditionError):
        evaluate_condition({"unknown_key": True}, ctx)
