# 运行诊断

OCR4game 在真实任务运行时会在 `runs/<game_id>_<timestamp>/` 下保存诊断产物。诊断功能只读取本地 trace、截图和配置，不会上传数据。

## 产物位置

一次正常任务运行会创建 run 目录，例如：

```text
runs/star_rail_20260624_153000/
  trace.jsonl
  fail_<step_id>.png
  report.md
  report.html
  replay_summary.json
  replay_report.md
  anchor_eval_summary.json
  anchor_eval_report.md
  anchor_eval_report.html
  overlays/
```

其中：

- `trace.jsonl`：结构化运行事件，每行一个 JSON object。
- `fail_<step_id>.png`：非 optional 动作失败时保存的截图。
- `report.md` / `report.html`：由 `ocr4game-report` 生成的诊断报告。
- `replay_summary.json` / `replay_report.md`：由 `ocr4game-replay` 生成的离线截图重放结果。
- `anchor_eval_summary.json` / `anchor_eval_report.md` / `anchor_eval_report.html`：由 `ocr4game-anchor-eval` 生成的离线 anchor 质量报告。
- `overlays/`：由 `ocr4game-anchor-eval --overlay` 生成的 bbox 标注图。

`--validate` 不会创建运行 trace。`--dry-run` 只做离线校验和窗口预检，也不会强制创建真实 run trace。

## 生成诊断报告

```powershell
ocr4game-report --run runs/star_rail_20260624_153000
```

报告包含：

1. Run Summary：游戏、任务、开始/结束时间、耗时、步骤数、状态计数。
2. Failure Summary：失败 step/action、消息、截图、锚点、匹配分数和 bbox。
3. Step Timeline：按 trace 顺序列出 step/action 事件。
4. Anchor Diagnostics：按 `anchor_name` 聚合次数、失败次数、score min/mean/max。
5. Artifacts：列出 trace 引用或 run 目录中的失败截图。

如果 run 目录没有 `trace.jsonl`，命令会输出清晰错误并返回非零退出码。

## 离线 replay

第一阶段 replay 不会执行 workflow、不会点击、不会绑定真实窗口。它只读取 run 目录中 trace 引用的截图，并使用当前配置中的 `Perception.evaluate_anchor()` 重新评估锚点。

```powershell
ocr4game-replay --run runs/star_rail_20260624_153000
ocr4game-replay --run runs/star_rail_20260624_153000 --step-index 12
ocr4game-replay --run runs/star_rail_20260624_153000 --anchor claim_button
```

replay 会生成：

- `replay_summary.json`：机器可读结果。
- `replay_report.md`：简短 Markdown 表格。

如果 trace 中没有 `screenshot_path`，replay 会提示无法重放并返回非零退出码。

## Anchor 离线评估

`ocr4game-anchor-eval` 会对截图目录中的图片逐张评估 anchor，并生成：

- `anchor_eval_summary.json`：完整机器可读结果。
- `anchor_eval_report.md`：按 anchor 聚合的 Markdown 报告。
- `anchor_eval_report.html`：传入 `--html` 时生成。
- `overlays/`：传入 `--overlay` 时保存 bbox、中心点和 ROI 标注图。

常用命令：

```powershell
ocr4game-anchor-eval --game star_rail --anchor claim_button --screenshots tests/fixtures/star_rail/frames --html --overlay
ocr4game-anchor-eval --game star_rail --include-ocr --screenshots tests/fixtures/star_rail/frames --output-dir runs/anchor_eval --html --overlay
```

每个 anchor 的核心统计字段：

| 字段 | 含义 |
|------|------|
| `num_images` | 参与评估的截图数量 |
| `visible_count` | 分数达到当前 threshold 的截图数量 |
| `missing_count` | 未达到 threshold 或读取失败的截图数量 |
| `score_min` | 最低匹配分数 |
| `score_mean` | 平均匹配分数 |
| `score_median` | 中位数匹配分数 |
| `score_p10` | 第 10 百分位分数，用于观察低分尾部 |
| `score_p90` | 第 90 百分位分数 |
| `recommended_threshold` | 基于低分位和安全 margin 的建议 threshold |
| `failure_examples` | 最多 5 个未匹配/失败样例，包含截图、score、bbox、overlay 等 |

OCR anchor 会在传入 `--include-ocr` 或 `--only-ocr` 时执行离线 OCR 评估；如果 OCR 环境不可用，报告中会写入 warning，template 部分仍继续生成。

## 内容识别诊断

`ocr4game-recognize` 会基于静态截图输出 Perception v2 内容快照：screen state、可见 anchors、OCR texts、content extractors 结果和 warnings。

```powershell
ocr4game-recognize --game star_rail --image tests/fixtures/star_rail/frames/daily_panel.png --json
ocr4game-recognize --game star_rail --images tests/fixtures/star_rail/frames --output-dir runs/recognize_batch
```

批量模式生成：

- `recognize_summary.json`
- `<stem>.content.json`
- `recognize_report.md`

## Workflow lint

`ocr4game-lint` 会复用基础离线校验，并额外检查更偏质量/风险的规则：

- 未定义 vars（基础 validate 已覆盖）。
- 未使用 vars。
- 不存在的 anchor（基础 validate 已覆盖）。
- 不存在的 action（基础 validate 已覆盖）。
- `loop.max` 非法、非正数或异常偏大。
- `retry` 非法、负数或异常偏大。
- optional action 后缺少 `log` / `wait_for` / `assert_window` 等诊断或恢复动作。
- `wait.ms` / `wait_for.timeout_ms` 非法、非正数或异常偏大。
- 同一 step 内连续重复点击同一 anchor。
- 明显恒 false 的静态 condition，例如字面量 `false`、空 `any: []`、或能用已知 vars 判断为 false 的比较。

`ocr4game --validate` 保持兼容；`ocr4game --validate --strict` 会额外包含 lint 结果，并继续沿用 warning 也失败的严格策略。

## trace.jsonl 字段

每行至少包含下列字段，缺失信息用 `null` 表示：

| 字段 | 含义 |
|------|------|
| `ts` | ISO 时间字符串 |
| `event` | 事件类型，如 `task_started`、`action_failed` |
| `game_id` | 游戏 ID |
| `task_id` | 任务 ID |
| `step_index` | step 序号 |
| `step_name` | step 名称或 id |
| `action_index` | 当前 action 序号 |
| `action_type` | action 类型 |
| `status` | `success` / `failed` / `skipped` / `optional_failed` / `retry` / `started` / `finished` |
| `message` | 简短说明 |
| `elapsed_ms` | 耗时（毫秒） |
| `retry_count` | 当前 retry 次数 |
| `anchor_name` | 锚点名称 |
| `condition` | 条件表达式摘要 |
| `condition_result` | 条件结果 |
| `matched_score` | template/OCR 匹配分数 |
| `matched_bbox` | `[x, y, w, h]`，可为空 |
| `roi` | `[x, y, w, h]`，可为空 |
| `screenshot_path` | 相对 run 目录的截图路径 |
| `extra` | 其他扩展诊断信息 |

## 常见诊断流程

1. 运行任务失败后，查看终端中最后的 step id。
2. 对 run 目录执行 `ocr4game-report --run ...`。
3. 在 `Failure Summary` 中找到失败 action、截图和 anchor。
4. 打开失败截图，确认 UI 是否在预期 ROI 内。
5. 用 `ocr4game-replay --run ... --anchor <anchor>` 离线复查当前模板/阈值是否能识别截图。
6. 如果 score 偏低，重新框选模板或用 `ocr4game-threshold --game star_rail --anchor <anchor> --sweep` 标定阈值。
