# CLI 参考

所有命令在安装 `pip install -e ".[dev]"` 后可用。未安装时可用 `python -m ocr4game.app` 等形式（见 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)）。

## 命令总览

| 命令 | 说明 |
|------|------|
| `ocr4game` | 运行 / 校验 / 预检任务 |
| `ocr4game-annotate` | 框选 UI，写入 `assets/ui/` 与 `profile.yaml` |
| `ocr4game-threshold` | 标定 template 锚点 threshold |
| `ocr4game-import` | 批量导入模板图片和 frames 到 assets 与 fixtures |

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
