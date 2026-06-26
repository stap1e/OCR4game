# CLI 参考

所有命令在安装 `pip install -e ".[dev]"` 后可用。未安装时可用 `python -m ocr4game.app` 等形式（见 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)）。

## 命令总览

| 命令 | 说明 |
|------|------|
| `ocr4game` | 运行 / 校验 / 预检任务 |
| `ocr4game-annotate` | 框选 UI，写入 `assets/ui/` 与 `profile.yaml` |
| `ocr4game-threshold` | 标定 template 锚点 threshold |
| `ocr4game-anchor-eval` | 离线批量评估 anchor 质量并生成报告 |
| `ocr4game-lint` | 静态检查 workflow 的风险配置 |
| `ocr4game-import` | 批量导入模板图片和 frames 到 assets 与 fixtures |
| `ocr4game-report` | 根据 run 目录中的 `trace.jsonl` 生成诊断报告 |
| `ocr4game-replay` | 使用 run 目录中的失败截图离线重新评估锚点 |

---

## `ocr4game`

### 参数

| 参数 | 说明 |
|------|------|
| `--game ID` | 游戏 ID（默认 `star_rail`） |
| `--task NAME` | 任务名 → `tasks/<name>.yaml` |
| `--var KEY=VALUE` | 覆盖任务 vars，可多次 |
| `--validate` | 仅离线校验（无需游戏） |
| `--dry-run` | 离线校验 + 窗口预检，不执行；不指定 `--task` 时使用 `daily` |
| `--strict` | 缺模板等资源也视为失败 |
| `--list-games` | 列出已注册 / 已配置游戏 |
| `--log-level LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `--version` | 版本号 |

### 示例

```powershell
ocr4game --list-games
ocr4game --validate --game star_rail --task daily
ocr4game --validate --strict --game star_rail --task daily
ocr4game --dry-run --game star_rail
ocr4game --game star_rail --task daily
ocr4game --game star_rail --task daily --var sweep_times=3 --var claim_loop_max=5
ocr4game --log-level DEBUG --game star_rail --task daily
```

### 退出码

| 码 | 含义 |
|----|------|
| `0` | 成功 |
| `1` | 配置 / 校验 / 预检失败 |
| `2` | 任务中止（步骤失败或 `max_run_minutes` 超时） |

运行产物：`runs/<game_id>_<timestamp>/`（`global.yaml` 的 `runs_dir`）。

---

## `ocr4game-annotate`

在游戏窗口上框选 UI，保存为模板 PNG 并更新 `profile.yaml` 锚点。

| 参数 | 说明 |
|------|------|
| `--game` | 游戏 ID（默认 `star_rail`） |
| `--name` | 锚点名称（必填），如 `claim_button` |
| `--threshold` | 写入 profile 的初始 threshold（默认 0.88） |

```powershell
ocr4game-annotate --game star_rail --name claim_button
```

操作：`Enter` 确认选区，`Esc` 取消。需游戏 **窗口化** 且在前台。

---

## `ocr4game-threshold`

标定 template 锚点匹配 threshold。

| 参数 | 说明 |
|------|------|
| `--game` | 游戏 ID |
| `--anchor` | 锚点名称（与 `--all` 二选一） |
| `--all` | 标定 profile 中全部 template 锚点 |
| `--frame PATH` | 离线静态截图（无需游戏） |
| `--margin` | 建议值 = confidence − margin（默认 0.03） |
| `--sweep` | 打印各 threshold 档位是否匹配 |
| `--apply` | 将建议 threshold 写回 `profile.yaml` |

```powershell
ocr4game-threshold --game star_rail --anchor claim_button --sweep
ocr4game-threshold --game star_rail --anchor claim_button --apply
ocr4game-threshold --game star_rail --all --frame screenshot.png
```

---

## `ocr4game-anchor-eval`

离线批量评估 anchor 在截图集上的匹配质量，不绑定窗口、不点击游戏。

| 参数 | 说明 |
|------|------|
| `--game` | 游戏 ID（默认 `star_rail`） |
| `--anchor NAME` | 只评估指定 anchor；可重复传入 |
| `--screenshots PATH` | 截图文件或目录；默认优先使用 `tests/fixtures/<game>/frames` |
| `--output-dir PATH` | 输出目录；默认写入 `runs/<game>_anchor_eval_<timestamp>/` |
| `--html` | 额外生成 `anchor_eval_report.html` |
| `--overlay` | 在 `overlays/` 下保存 bbox 标注图 |
| `--include-ocr` | 同时评估 OCR anchor，OCR 不可用时写 warning 并继续 template 部分 |
| `--only-ocr` | 只评估 OCR anchor |

```powershell
ocr4game-anchor-eval --game star_rail
ocr4game-anchor-eval --game star_rail --anchor claim_button
ocr4game-anchor-eval --game star_rail --screenshots fixtures/star_rail/screenshots
ocr4game-anchor-eval --game star_rail --anchor claim_button --html --overlay
ocr4game-anchor-eval --game star_rail --include-ocr --screenshots tests/fixtures/star_rail/frames
ocr4game-anchor-eval --game star_rail --only-ocr
```

输出文件：

- `anchor_eval_summary.json`：机器可读统计。
- `anchor_eval_report.md`：Markdown 报告。
- `anchor_eval_report.html`：仅 `--html` 时生成。
- `overlays/*.png`：仅 `--overlay` 时生成。

---

## `ocr4game-recognize`

离线识别截图内容，不绑定窗口、不点击游戏。输出包含 `game_id`、`image_path`、`screen_state`、`anchors`、`texts`、`extracted` 和 `warnings`。

| 参数 | 说明 |
|------|------|
| `--game` | 游戏 ID（默认 `star_rail`） |
| `--image PATH` | 单张截图 |
| `--images DIR` | 截图目录，批量模式 |
| `--json` | 单图模式打印结构化 JSON |
| `--output PATH` | 单图 JSON 输出路径 |
| `--output-dir PATH` | 批量输出目录，默认写入 `runs/<game>_recognize_<timestamp>/` |

```powershell
ocr4game-recognize --game star_rail --image tests/fixtures/star_rail/frames/daily_panel.png
ocr4game-recognize --game star_rail --image tests/fixtures/star_rail/frames/daily_panel.png --json
ocr4game-recognize --game star_rail --images tests/fixtures/star_rail/frames --output-dir runs/recognize_batch
```

批量模式生成 `recognize_summary.json`、每张图一个 `<stem>.content.json` 和 `recognize_report.md`。

---

## `ocr4game-lint`

静态检查 workflow 中不一定会被基础 validate 拦截、但运行时风险较高的配置。

| 参数 | 说明 |
|------|------|
| `--game` | 游戏 ID（默认 `star_rail`） |
| `--task` | 任务名（默认 `daily`） |
| `--var KEY=VALUE` | 覆盖任务 vars，可多次 |
| `--strict` | warning 也视为失败 |

```powershell
ocr4game-lint --game star_rail --task daily
ocr4game-lint --game star_rail --task daily --strict
```

lint 会复用基础离线校验，并额外检查未使用 vars、过大的 `loop.max` / `retry`、可疑 timeout、optional action 后缺少诊断/恢复、同 step 连续重复点击同一 anchor、以及明显恒 false 的条件。

---

## `ocr4game-import`

从目录批量导入模板图片和 frames。

| 参数 | 说明 |
|------|------|
| `--game` | 游戏 ID |
| `--from-dir PATH` | 源目录（必填） |
| `--no-fixtures` | 不同步到 `tests/fixtures/` |

目录结构示例：

```text
captures/star_rail/
  ui/
    ui/claim_button.png              # 路径可与 profile 中 anchors.*.image 一致
    ui/buttons/confirm_button.png    # 支持子目录，避免同名模板冲突
  frames/                            # 可选 → tests/fixtures/.../frames/
    daily_panel.png
    nested/debug_frame.jpg           # 支持 .png/.jpg/.jpeg/.webp
```

也支持扁平目录：若源目录没有 `ui/` 和 `frames/`，会按模板文件名匹配 `anchors.*.image`。

```powershell
ocr4game-import --game star_rail --from-dir D:\captures\star_rail
```

---

## `ocr4game-report`

根据 run 目录中的 `trace.jsonl` 生成 `report.md` 和 `report.html`。

| 参数 | 说明 |
|------|------|
| `--run PATH` | run 目录，如 `runs/star_rail_20260624_153000` |

```powershell
ocr4game-report --run runs/star_rail_20260624_153000
```

如果没有 `trace.jsonl`，命令返回非零退出码。

---

## `ocr4game-replay`

离线读取 run 目录中 trace 引用的截图，使用当前配置重新评估锚点；不会绑定窗口、点击或执行 workflow。

| 参数 | 说明 |
|------|------|
| `--run PATH` | run 目录 |
| `--step-index N` | 只 replay 指定 step_index 的截图 |
| `--anchor NAME` | 只评估指定锚点 |

```powershell
ocr4game-replay --run runs/star_rail_20260624_153000
ocr4game-replay --run runs/star_rail_20260624_153000 --step-index 12
ocr4game-replay --run runs/star_rail_20260624_153000 --anchor claim_button
```

输出 `replay_summary.json` 和 `replay_report.md`。更多字段说明见 [diagnostics.md](diagnostics.md)。

---

## 插件注册（entry_points）

新游戏在 `pyproject.toml` 声明，**无需改** `registry.py`：

```toml
[project.entry-points."ocr4game.plugins"]
my_game = "ocr4game.games.my_game.plugin:MyGamePlugin"
```

```powershell
pip install -e ".[dev]"
ocr4game --list-games    # 显示 [entry-point] 或 [builtin]
```

详见 [ADDING_A_GAME.md](ADDING_A_GAME.md)。
