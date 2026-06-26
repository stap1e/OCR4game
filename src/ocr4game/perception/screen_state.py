"""Screen-state recognition from anchors and OCR rules."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import numpy as np

from ocr4game.config import GameProfile
from ocr4game.perception.content import ScreenStateResult
from ocr4game.perception.ocr_eval import match_texts


@dataclass
class _RuleResult:
    matched: bool
    label: str


class ScreenStateRecognizer:
    def recognize(self, frame: np.ndarray, profile: GameProfile, perception: Any) -> ScreenStateResult:
        best: ScreenStateResult | None = None
        for state_name, config in profile.screen_states.items():
            required = [_eval_rule(rule, frame, perception) for rule in config.require]
            optional = [_eval_rule(rule, frame, perception) for rule in config.optional]
            rejected = [_eval_rule(rule, frame, perception) for rule in config.reject]

            matched_rules = [item.label for item in required + optional if item.matched]
            failed_rules = [item.label for item in required + optional if not item.matched]
            reject_hits = [item.label for item in rejected if item.matched]
            if reject_hits:
                failed_rules.extend(f"reject:{label}" for label in reject_hits)
                continue
            if any(not item.matched for item in required):
                continue

            required_score = 0.7 if required else 0.3
            optional_score = 0.0
            if optional:
                optional_score = 0.3 * (sum(1 for item in optional if item.matched) / len(optional))
            confidence = min(1.0, required_score + optional_score)
            candidate = ScreenStateResult(state_name, confidence, matched_rules, failed_rules)
            if best is None or candidate.confidence > best.confidence:
                best = candidate

        if best is None:
            return ScreenStateResult("unknown", 0.0, [], [])
        return best


def _eval_rule(rule: Any, frame: np.ndarray, perception: Any) -> _RuleResult:
    if not isinstance(rule, dict) or len(rule) != 1:
        return _RuleResult(False, f"invalid:{rule!r}")
    key, value = next(iter(rule.items()))
    if key == "anchor_visible":
        result = perception.evaluate_anchor(frame, str(value))
        return _RuleResult(bool(result.found), f"anchor_visible:{value}")
    if key == "anchor_missing":
        result = perception.evaluate_anchor(frame, str(value))
        return _RuleResult(not bool(result.found), f"anchor_missing:{value}")
    if key == "ocr_contains":
        texts = _read_texts(frame, perception)
        return _RuleResult(match_texts(texts, str(value), mode="normalized_contains").matched, f"ocr_contains:{value}")
    if key == "ocr_contains_any":
        texts = _read_texts(frame, perception)
        expected = value if isinstance(value, list) else [str(value)]
        return _RuleResult(match_texts(texts, expected, mode="normalized_contains").matched, f"ocr_contains_any:{expected}")
    if key == "ocr_regex":
        texts = _read_texts(frame, perception)
        matched = any(re.search(str(value), text) for text in texts)
        return _RuleResult(matched, f"ocr_regex:{value}")
    if key == "all" and isinstance(value, list):
        results = [_eval_rule(item, frame, perception) for item in value]
        return _RuleResult(all(item.matched for item in results), "all")
    if key == "any" and isinstance(value, list):
        results = [_eval_rule(item, frame, perception) for item in value]
        return _RuleResult(any(item.matched for item in results), "any")
    if key == "not":
        result = _eval_rule(value, frame, perception)
        return _RuleResult(not result.matched, f"not:{result.label}")
    return _RuleResult(False, f"unknown:{key}")


def _read_texts(frame: np.ndarray, perception: Any) -> list[str]:
    try:
        hits = perception.read_texts(frame)
    except AttributeError:
        hits = perception._ocr.read(frame)  # noqa: SLF001 - compatibility with existing Perception wrapper
    except Exception:
        return []
    return [str(getattr(hit, "text", hit)) for hit in hits]


def rule_anchor_refs(rule: Any) -> set[str]:
    refs: set[str] = set()
    if not isinstance(rule, dict):
        return refs
    for key, value in rule.items():
        if key in {"anchor_visible", "anchor_missing"} and isinstance(value, str):
            refs.add(value)
        elif key in {"all", "any"} and isinstance(value, list):
            for item in value:
                refs.update(rule_anchor_refs(item))
        elif key == "not":
            refs.update(rule_anchor_refs(value))
    return refs


def rule_label(rule: Any) -> str:
    if not isinstance(rule, dict) or len(rule) != 1:
        return repr(rule)
    key, value = next(iter(rule.items()))
    return f"{key}:{value}"


__all__ = ["ScreenStateRecognizer", "rule_anchor_refs", "rule_label"]
