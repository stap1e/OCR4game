import pytest

from ocr4game.workflow.vars import (
    InvalidVarAssignmentError,
    UndefinedVarError,
    coerce_var_value,
    parse_var_assignment,
    resolve_value,
)


def test_resolve_scalar_preserves_type() -> None:
    vars = {"sweep_times": 3, "panel_wait_ms": 1200}
    assert resolve_value("{sweep_times}", vars) == 3
    assert resolve_value("{panel_wait_ms}", vars) == 1200
    assert isinstance(resolve_value("{sweep_times}", vars), int)


def test_resolve_nested_structure() -> None:
    vars = {"claim_loop_max": 5, "anchor": "claim_button"}
    raw = {
        "loop": {"max": "{claim_loop_max}"},
        "do": [{"click_template": {"anchor": "{anchor}"}}],
    }
    resolved = resolve_value(raw, vars)
    assert resolved["loop"]["max"] == 5
    assert resolved["do"][0]["click_template"]["anchor"] == "claim_button"


def test_resolve_partial_string_substitution() -> None:
    vars = {"sweep_times": 2}
    assert resolve_value("扫荡 {sweep_times} 次", vars) == "扫荡 2 次"


def test_undefined_var_raises() -> None:
    with pytest.raises(UndefinedVarError, match="missing"):
        resolve_value("{missing}", {})

    with pytest.raises(UndefinedVarError, match="missing"):
        resolve_value("hello {missing}", {"other": 1})


def test_coerce_var_value() -> None:
    assert coerce_var_value("3") == 3
    assert coerce_var_value("1.5") == 1.5
    assert coerce_var_value("true") is True
    assert coerce_var_value("false") is False
    assert coerce_var_value("hello") == "hello"


def test_parse_var_assignment() -> None:
    assert parse_var_assignment("sweep_times=3") == ("sweep_times", 3)
    assert parse_var_assignment(" panel_wait_ms = 900 ") == ("panel_wait_ms", 900)
    assert parse_var_assignment("enabled=false") == ("enabled", False)


def test_parse_var_assignment_invalid() -> None:
    with pytest.raises(InvalidVarAssignmentError):
        parse_var_assignment("noequals")

    with pytest.raises(InvalidVarAssignmentError):
        parse_var_assignment("123bad=1")
