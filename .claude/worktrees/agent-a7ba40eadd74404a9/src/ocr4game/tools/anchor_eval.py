"""Offline anchor evaluation CLI and report generation."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from ocr4game.config import (
    GameProfile,
    OcrAnchorConfig,
    TemplateAnchorConfig,
    load_game_profile,
    load_global_config,
)
from ocr4game.perception.ocr_eval import evaluate_ocr_anchor
from ocr4game.perception.roi import roi_offset
from ocr4game.perception.template import TemplateMatcher
from ocr4game.resources import game_assets_dir, repo_root, runs_base_dir
from ocr4game.tools.report import render_html
from ocr4game.tools.threshold import suggest_threshold

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True)
class AnchorEvalItem:
    screenshot: str
    visible: bool
    score: float | None
    center: tuple[int, int] | None
    bbox: tuple[int, int, int, int] | None
    error: str | None = None
    overlay: str | None = None


def discover_screenshots(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise FileNotFoundError(f"截图目录不存在: {path}")
    return sorted(
        item for item in path.rglob("*") if item.is_file() and item.suffix.lower() in _IMAGE_SUFFIXES
    )


def default_screenshots_dir(game_id: str) -> Path | None:
    path = repo_root() / "tests" / "fixtures" / game_id / "frames"
    return path if path.is_dir() else None


def default_output_dir(profile: GameProfile) -> Path:
    global_cfg = load_global_config()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return runs_base_dir(global_cfg) / f"{profile.game_id}_anchor_eval_{stamp}"


def evaluate_anchors(
    profile: GameProfile,
    screenshots: list[Path],
    *,
    anchor_names: list[str] | None = None,
    output_dir: Path | None = None,
    write_overlays: bool = False,
    include_ocr: bool = False,
    only_ocr: bool = False,
) -> dict[str, Any]:
    selected = anchor_names or sorted(profile.anchors)
    matcher = TemplateMatcher()
    output_dir = output_dir or default_output_dir(profile)
    overlay_dir = output_dir / "overlays"
    if write_overlays:
        overlay_dir.mkdir(parents=True, exist_ok=True)

    anchors: dict[str, Any] = {}
    warnings: list[str] = []
    for anchor_name in selected:
        anchor = profile.anchors.get(anchor_name)
        if anchor is None:
            anchors[anchor_name] = _unsupported_summary(
                len(screenshots), f"未定义的锚点: {anchor_name}"
            )
            continue
        if isinstance(anchor, OcrAnchorConfig):
            if include_ocr or only_ocr:
                summary = evaluate_ocr_anchor(profile, anchor_name, anchor, screenshots)
                if summary.get("warning"):
                    warnings.append(f"{anchor_name}: {summary['warning']}")
                anchors[anchor_name] = summary
            else:
                anchors[anchor_name] = _unsupported_summary(len(screenshots), "OCR 锚点暂不支持离线批量评估（使用 --include-ocr 启用）")
            continue
        if only_ocr:
            continue
        if not isinstance(anchor, TemplateAnchorConfig):
            anchors[anchor_name] = _unsupported_summary(len(screenshots), "未知锚点类型")
            continue
        anchors[anchor_name] = _evaluate_template_anchor(
            profile,
            anchor_name,
            anchor,
            screenshots,
            matcher,
            overlay_dir=overlay_dir,
            write_overlays=write_overlays,
            output_dir=output_dir,
        )

    return {
        "game_id": profile.game_id,
        "num_images": len(screenshots),
        "screenshots": [str(path) for path in screenshots],
        "anchors": anchors,
        "warnings": warnings,
    }


def _evaluate_template_anchor(
    profile: GameProfile,
    anchor_name: str,
    anchor: TemplateAnchorConfig,
    screenshots: list[Path],
    matcher: TemplateMatcher,
    *,
    overlay_dir: Path,
    write_overlays: bool,
    output_dir: Path,
) -> dict[str, Any]:
    template_path = game_assets_dir(profile) / anchor.image
    template = cv2.imread(str(template_path)) if template_path.is_file() else None
    items: list[AnchorEvalItem] = []

    for screenshot in screenshots:
        frame = cv2.imread(str(screenshot))
        if frame is None:
            items.append(
                AnchorEvalItem(
                    screenshot=str(screenshot),
                    visible=False,
                    score=None,
                    center=None,
                    bbox=None,
                    error="无法读取截图",
                )
            )
            continue
        if template is None:
            items.append(
                AnchorEvalItem(
                    screenshot=str(screenshot),
                    visible=False,
                    score=None,
                    center=None,
                    bbox=None,
                    error=f"模板不存在或无法读取: {template_path}",
                )
            )
            continue

        result = matcher.confidence(
            frame,
            template_path,
            roi=anchor.roi,
            scales=anchor.scales,
            match_mode=anchor.match_mode,
        )
        bbox = _bbox_from_match(result.top_left, template)
        visible = result.confidence >= anchor.threshold
        overlay_rel = None
        if write_overlays:
            overlay_path = _write_overlay(
                frame,
                anchor_name=anchor_name,
                score=result.confidence,
                visible=visible,
                bbox=bbox,
                center=result.center,
                roi=anchor.roi,
                source=screenshot,
                overlay_dir=overlay_dir,
            )
            overlay_rel = str(overlay_path.relative_to(output_dir))

        items.append(
            AnchorEvalItem(
                screenshot=str(screenshot),
                visible=visible,
                score=result.confidence,
                center=result.center,
                bbox=bbox,
                overlay=overlay_rel,
            )
        )

    return _summarize_items(anchor, template_path, items)


def _bbox_from_match(top_left: tuple[int, int], template: np.ndarray) -> tuple[int, int, int, int]:
    h, w = template.shape[:2]
    x, y = top_left
    return (x, y, x + w, y + h)


def _write_overlay(
    frame: np.ndarray,
    *,
    anchor_name: str,
    score: float,
    visible: bool,
    bbox: tuple[int, int, int, int],
    center: tuple[int, int],
    roi: list[float] | None,
    source: Path,
    overlay_dir: Path,
) -> Path:
    image = frame.copy()
    color = (0, 200, 0) if visible else (0, 0, 255)
    x1, y1, x2, y2 = bbox
    cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
    cv2.circle(image, center, 4, color, -1)
    if roi:
        ox, oy = roi_offset(roi, frame.shape[:2])
        rx2 = ox + round((roi[2] - roi[0]) * frame.shape[1])
        ry2 = oy + round((roi[3] - roi[1]) * frame.shape[0])
        cv2.rectangle(image, (ox, oy), (rx2, ry2), (255, 180, 0), 1)
    label = f"{anchor_name} {score:.3f} {'match' if visible else 'miss'}"
    cv2.putText(image, label, (max(0, x1), max(18, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
    safe_anchor = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in anchor_name)
    path = overlay_dir / f"{source.stem}_{safe_anchor}.png"
    cv2.imwrite(str(path), image)
    return path


def _summarize_items(
    anchor: TemplateAnchorConfig,
    template_path: Path,
    items: list[AnchorEvalItem],
) -> dict[str, Any]:
    scores = [item.score for item in items if item.score is not None]
    visible_count = sum(1 for item in items if item.visible)
    p10 = _percentile(scores, 10)
    p90 = _percentile(scores, 90)
    recommended = suggest_threshold(p10) if p10 is not None else None
    failures = [item for item in items if not item.visible or item.error]
    return {
        "type": "template",
        "template": str(template_path),
        "threshold": anchor.threshold,
        "num_images": len(items),
        "visible_count": visible_count,
        "missing_count": len(items) - visible_count,
        "score_min": min(scores) if scores else None,
        "score_mean": float(np.mean(scores)) if scores else None,
        "score_median": float(np.median(scores)) if scores else None,
        "score_p10": p10,
        "score_p90": p90,
        "recommended_threshold": recommended,
        "failure_examples": [_item_to_dict(item) for item in failures[:5]],
        "examples": [_item_to_dict(item) for item in items],
    }


def _unsupported_summary(num_images: int, reason: str) -> dict[str, Any]:
    return {
        "type": "unsupported",
        "num_images": num_images,
        "visible_count": 0,
        "missing_count": num_images,
        "score_min": None,
        "score_mean": None,
        "score_median": None,
        "score_p10": None,
        "score_p90": None,
        "recommended_threshold": None,
        "failure_examples": [],
        "error": reason,
    }


def _percentile(values: list[float], q: int) -> float | None:
    if not values:
        return None
    return float(np.percentile(values, q))


def _item_to_dict(item: AnchorEvalItem) -> dict[str, Any]:
    return {
        "screenshot": item.screenshot,
        "visible": item.visible,
        "score": item.score,
        "center": list(item.center) if item.center is not None else None,
        "bbox": list(item.bbox) if item.bbox is not None else None,
        "error": item.error,
        "overlay": item.overlay,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = ["# OCR4game Anchor Evaluation", ""]
    lines.extend(
        [
            "## Summary",
            "",
            f"- game_id: `{summary['game_id']}`",
            f"- num_images: `{summary['num_images']}`",
            f"- anchors: `{len(summary['anchors'])}`",
            "",
        ]
    )
    lines.extend(["## Anchor Statistics", ""])
    lines.append(
        "| Anchor | Type | Images | Visible | Missing | Score min | Score mean | Score median | P10 | P90 | Recommended threshold |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for name, item in sorted(summary["anchors"].items()):
        lines.append(
            "| "
            + " | ".join(
                [
                    name,
                    str(item.get("type", "")),
                    str(item.get("num_images", 0)),
                    str(item.get("visible_count", 0)),
                    str(item.get("missing_count", 0)),
                    _fmt(item.get("score_min")),
                    _fmt(item.get("score_mean")),
                    _fmt(item.get("score_median")),
                    _fmt(item.get("score_p10")),
                    _fmt(item.get("score_p90")),
                    _fmt(item.get("recommended_threshold")),
                ]
            )
            + " |"
        )
    lines.append("")

    ocr_items = {name: item for name, item in summary["anchors"].items() if item.get("type") == "ocr"}
    if ocr_items:
        lines.extend(["## OCR Anchor Diagnostics", ""])
        lines.append("| Anchor | Images | Hit | Miss | Hit rate | Score mean | Examples | Warning |")
        lines.append("|---|---:|---:|---:|---:|---:|---|---|")
        for name, item in sorted(ocr_items.items()):
            lines.append(
                "| "
                + " | ".join(
                    [
                        name,
                        str(item.get("num_images", 0)),
                        str(item.get("hit_count", 0)),
                        str(item.get("miss_count", 0)),
                        _fmt(item.get("hit_rate")),
                        _fmt(item.get("score_mean")),
                        ", ".join(item.get("text_examples") or []),
                        str(item.get("warning") or ""),
                    ]
                )
                + " |"
            )
        lines.append("")

    lines.extend(["## Failure Examples", ""])
    for name, item in sorted(summary["anchors"].items()):
        failures = item.get("failure_examples") or []
        if not failures and not item.get("error"):
            continue
        lines.append(f"### {name}")
        if item.get("error"):
            lines.append(f"- error: `{item['error']}`")
        for failure in failures:
            lines.append(
                f"- `{failure.get('screenshot')}` score=`{_fmt(failure.get('score'))}` "
                f"bbox=`{failure.get('bbox')}` error=`{failure.get('error') or ''}`"
            )
        lines.append("")
    return "\n".join(lines)


def write_reports(summary: dict[str, Any], output_dir: Path, *, html: bool) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "anchor_eval_summary.json"
    md_path = output_dir / "anchor_eval_report.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown = render_markdown(summary)
    md_path.write_text(markdown, encoding="utf-8")
    paths = {"json": json_path, "markdown": md_path}
    if html:
        html_path = output_dir / "anchor_eval_report.html"
        html_path.write_text(render_html(markdown), encoding="utf-8")
        paths["html"] = html_path
    return paths


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="离线评估 anchor 在截图集上的匹配质量")
    parser.add_argument("--game", default="star_rail")
    parser.add_argument("--anchor", action="append", help="只评估指定锚点，可重复")
    parser.add_argument("--screenshots", type=Path, help="截图文件或目录")
    parser.add_argument("--output-dir", type=Path, help="输出目录，默认写入 runs/<game>_anchor_eval_<time>")
    parser.add_argument("--html", action="store_true", help="额外生成 HTML 报告")
    parser.add_argument("--overlay", action="store_true", help="保存 bbox overlay 图片")
    parser.add_argument("--include-ocr", action="store_true", help="同时评估 OCR anchor")
    parser.add_argument("--only-ocr", action="store_true", help="只评估 OCR anchor")
    args = parser.parse_args(argv)

    try:
        profile = load_game_profile(args.game)
        screenshot_root = args.screenshots or default_screenshots_dir(args.game)
        if screenshot_root is None:
            parser.error("未找到默认 fixtures 截图目录，请指定 --screenshots")
        screenshots = discover_screenshots(screenshot_root)
        if not screenshots:
            raise FileNotFoundError(f"未找到截图: {screenshot_root}")
        output_dir = args.output_dir or default_output_dir(profile)
        summary = evaluate_anchors(
            profile,
            screenshots,
            anchor_names=args.anchor,
            output_dir=output_dir,
            write_overlays=args.overlay,
            include_ocr=args.include_ocr,
            only_ocr=args.only_ocr,
        )
        paths = write_reports(summary, output_dir, html=args.html)
    except Exception as exc:
        print(f"anchor evaluation 失败: {exc}", file=sys.stderr)
        return 1

    for path in paths.values():
        print(f"已生成: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
