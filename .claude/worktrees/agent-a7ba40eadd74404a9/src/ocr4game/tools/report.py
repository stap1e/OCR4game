"""Generate markdown/HTML diagnostics reports from run trace files."""

from __future__ import annotations

import argparse
import html
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _load_trace(run_dir: Path) -> list[dict[str, Any]]:
    trace_path = run_dir / "trace.jsonl"
    if not trace_path.is_file():
        raise FileNotFoundError(f"未找到 trace 文件: {trace_path}")

    records: list[dict[str, Any]] = []
    with trace_path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"trace 第 {line_no} 行不是有效 JSON: {exc}") from exc
            if isinstance(item, dict):
                records.append(item)
    return records


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, list | tuple):
        return ", ".join(_fmt(v) for v in value)
    return str(value)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _summarize(records: list[dict[str, Any]], run_dir: Path) -> dict[str, Any]:
    game_id = next((r.get("game_id") for r in records if r.get("game_id")), "")
    task_id = next((r.get("task_id") for r in records if r.get("task_id")), "")
    start = records[0].get("ts") if records else ""
    end = records[-1].get("ts") if records else ""
    elapsed = next(
        (r.get("elapsed_ms") for r in reversed(records) if r.get("event") == "task_finished"),
        None,
    )
    statuses = Counter(_fmt(r.get("status")) for r in records if r.get("status") is not None)
    events = Counter(_fmt(r.get("event")) for r in records if r.get("event") is not None)
    step_names = {r.get("step_name") for r in records if r.get("step_name")}
    failures = [
        r
        for r in records
        if r.get("status") in {"failed", "optional_failed"}
        or str(r.get("event", "")).endswith("failed")
    ]

    anchors: dict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "failed": 0, "scores": []})
    for record in records:
        anchor = record.get("anchor_name")
        if not anchor:
            continue
        item = anchors[str(anchor)]
        item["count"] += 1
        if record.get("status") in {"failed", "optional_failed"}:
            item["failed"] += 1
        score = record.get("matched_score")
        if isinstance(score, int | float):
            item["scores"].append(float(score))

    artifacts = sorted(
        {
            str(r.get("screenshot_path"))
            for r in records
            if r.get("screenshot_path")
        }
    )
    for path in run_dir.glob("fail_*.png"):
        artifacts.append(path.name)
    artifacts = sorted(set(artifacts))

    return {
        "game_id": game_id,
        "task_id": task_id,
        "start": start,
        "end": end,
        "elapsed": elapsed,
        "statuses": statuses,
        "events": events,
        "total_steps": len(step_names),
        "failures": failures,
        "anchors": anchors,
        "artifacts": artifacts,
    }


def render_markdown(records: list[dict[str, Any]], run_dir: Path) -> str:
    summary = _summarize(records, run_dir)
    lines = ["# OCR4game Run Report", ""]
    lines.extend(
        [
            "## Run Summary",
            "",
            f"- game_id: `{summary['game_id']}`",
            f"- task_id: `{summary['task_id']}`",
            f"- start: `{summary['start']}`",
            f"- end: `{summary['end']}`",
            f"- total elapsed: `{_fmt(summary['elapsed'])} ms`",
            f"- total steps: `{summary['total_steps']}`",
            f"- status counts: `{dict(summary['statuses'])}`",
            f"- retry count: `{summary['events'].get('step_retry', 0)}`",
            "",
        ]
    )

    lines.extend(["## Failure Summary", ""])
    failures = summary["failures"]
    if failures:
        lines.append("| Step | Action | Status | Message | Screenshot | Anchor | Score | BBox |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for record in failures:
            lines.append(
                "| "
                + " | ".join(
                    _fmt(record.get(key)).replace("|", "\\|")
                    for key in (
                        "step_name",
                        "action_type",
                        "status",
                        "message",
                        "screenshot_path",
                        "anchor_name",
                        "matched_score",
                        "matched_bbox",
                    )
                )
                + " |"
            )
    else:
        lines.append("No failed events recorded.")
    lines.append("")

    lines.extend(["## Step Timeline", ""])
    lines.append("| # | Time | Event | Step | Action | Status | Message | Elapsed ms |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for index, record in enumerate(records, start=1):
        lines.append(
            "| "
            + " | ".join(
                _fmt(value).replace("|", "\\|")
                for value in (
                    index,
                    record.get("ts"),
                    record.get("event"),
                    record.get("step_name"),
                    record.get("action_type"),
                    record.get("status"),
                    record.get("message"),
                    record.get("elapsed_ms"),
                )
            )
            + " |"
        )
    lines.append("")

    lines.extend(["## Anchor Diagnostics", ""])
    if summary["anchors"]:
        lines.append("| Anchor | Count | Failed | Score min | Score mean | Score max |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for anchor, item in sorted(summary["anchors"].items()):
            scores = item["scores"]
            lines.append(
                f"| {anchor} | {item['count']} | {item['failed']} | "
                f"{_fmt(min(scores) if scores else None)} | "
                f"{_fmt(_mean(scores) if scores else None)} | "
                f"{_fmt(max(scores) if scores else None)} |"
            )
    else:
        lines.append("No anchor events recorded.")
    lines.append("")

    lines.extend(["## Artifacts", ""])
    if summary["artifacts"]:
        lines.extend(f"- `{artifact}`" for artifact in summary["artifacts"])
    else:
        lines.append("No screenshots or failure images recorded.")
    lines.append("")
    return "\n".join(lines)


def render_html(markdown: str) -> str:
    body = html.escape(markdown)
    return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
<meta charset=\"utf-8\">
<title>OCR4game Run Report</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.5; }}
pre {{ background: #f6f8fa; padding: 1rem; overflow: auto; }}
</style>
</head>
<body>
<pre>{body}</pre>
</body>
</html>
"""


def generate_report(run_dir: Path) -> tuple[Path, Path]:
    records = _load_trace(run_dir)
    markdown = render_markdown(records, run_dir)
    html_doc = render_html(markdown)
    md_path = run_dir / "report.md"
    html_path = run_dir / "report.html"
    md_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(html_doc, encoding="utf-8")
    return md_path, html_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成 OCR4game run 诊断报告")
    parser.add_argument("--run", required=True, help="run 目录，如 runs/star_rail_20260101_120000")
    args = parser.parse_args(argv)

    run_dir = Path(args.run)
    try:
        md_path, html_path = generate_report(run_dir)
    except Exception as exc:
        print(f"生成报告失败: {exc}", file=sys.stderr)
        return 1

    print(f"已生成: {md_path}")
    print(f"已生成: {html_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
