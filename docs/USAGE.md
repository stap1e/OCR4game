# 使用指南

本文档说明从零到跑通《崩坏：星穹铁道》日常的完整流程。其他游戏见 [ADDING_A_GAME.md](ADDING_A_GAME.md)。

## 1. 安装

**环境**：Windows 10/11、Python 3.11+（推荐 3.11 或 3.12）、游戏 **窗口化**（星穹铁道推荐客户区 **1280×720**，见 `profile.yaml`）。

> `rapidocr-onnxruntime` 在不同 Python 版本上的 wheel 支持可能不同。如果 OCR 依赖安装失败，优先尝试 Python 3.11/3.12，并先执行 `python -m pip install --upgrade pip`。

```powershell
cd c:\Users\16025\PythonProjects\OCR4game
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass  # 如 PowerShell 拦截激活脚本，可先执行这一行
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

只安装运行依赖时可用：

```powershell
pip install -e .
```

安装后可用命令：

| 命令 | 作用 |
|------|------|
| `ocr4game` | 运行任务 |
| `ocr4game-annotate` | 框选 UI 生成模板 |
| `ocr4game-threshold` | 标定匹配阈值 |
| `ocr4game-import` | 批量导入截图 |

验证安装：

```powershell
ocr4game --version
ocr4game --list-games
```

如果命令不可用，确认虚拟环境已激活，或用模块方式运行：

```powershell
python -m ocr4game.app --list-games
```

---

## 2. 第一次使用（推荐顺序）

```text
安装 → 校验配置 → 准备模板 → 标定阈值 → 预检窗口 → 跑 daily
```

### 2.1 启动游戏

- 窗口模式，不要用全屏独占
- 客户区 **1280×720**（与游戏内「显示模式 → 分辨率」一致；若改分辨率需同步 `profile.yaml`）

### 2.1.1 确认窗口与进程名（`profile.yaml`）

配置里填的是 **可执行文件名**（如 `StarRail.exe`），**不是**任务管理器里的 PID（进程号每次启动都会变）。

| 你在系统里看到的 | 是否写入 `profile.yaml` | 对应字段 |
|------------------|-------------------------|----------|
| 任务管理器 → 应用 → **Star Rail** | 否（这是显示名） | — |
| 窗口标题栏 **崩坏：星穹铁道** | 是 | `window.title_contains` |
| 属性 → 文件名 **StarRail.exe** | 是 | `window.process_names` |
| 详细信息 → **PID**（如 12345） | 否 | — |

**国服（miHoYo 启动器）查进程名：**

1. `Ctrl + Shift + Esc` 打开任务管理器 → **应用** 页找到 **Star Rail**
2. 右键 **Star Rail** → **属性**（或打开文件所在位置）
3. 在「常规」页看 **文件名**：`StarRail.exe` → 填入 `process_names`
4. 典型安装路径：`C:\Program Files\miHoYo Launcher\games\Star Rail Game\StarRail.exe`

**用命令自动核对（游戏窗口化运行中）：**

```powershell
ocr4game-annotate --game star_rail --list-windows
```

期望输出含 `process=StarRail.exe`、`size=1280x720`、`title='崩坏：星穹铁道'` 且带 `<-- 已选`。

**PowerShell 备选：**

```powershell
Get-Process | Where-Object { $_.ProcessName -eq 'StarRail' } |
  Select-Object Id, ProcessName, Path, MainWindowTitle
```

- 用 **ProcessName** → 配置为 `StarRail.exe`
- **Id** 仅用于排查，不要写入 YAML

当前星穹铁道默认配置见 `configs/games/star_rail/profile.yaml` 的 `window` 块；若 `--list-windows` 无结果，检查游戏是否窗口化、分辨率是否与 `resolution` 一致。

### 2.2 离线校验（无需开游戏）

```powershell
ocr4game --validate --game star_rail --task daily
```

通过表示任务 YAML、锚点引用、vars 语法正确。缺模板 PNG 时为 **warning**；加 `--strict` 则视为失败。

### 2.3 准备 UI 模板

**方式 A — 游戏内框选（推荐，1280×720 实机分辨率）**

```powershell
ocr4game-annotate --game star_rail --name main_menu_marker
ocr4game-annotate --game star_rail --name claim_button
# … 按需截取 profile.yaml 里列出的各锚点
```

操作：弹出窗口后 **拖拽框选** UI → `Enter` 确认 → 自动保存 PNG 并更新 `profile.yaml`。如果游戏界面切错或 UI 变化，按 `R` 重新抓取当前游戏画面；按 `Esc` 取消退出。选区过小时不会保存，可直接重新拖拽。

**方式 B — 导入已有截图**

```powershell
ocr4game-import --game star_rail --from-dir D:\captures\star_rail
```

目录可使用 `ui/` 和 `frames/` 子目录；UI 模板会按 `profile.yaml` 里 `anchors.*.image` 的相对路径匹配，frames 支持 `.png`、`.jpg`、`.jpeg`、`.webp`：

```text
D:\captures\star_rail\
  ui\
    ui\claim_button.png
    ui\buttons\confirm_button.png
  frames\
    daily_panel.png
    nested\debug_frame.jpg
```

默认会同步到 `tests/fixtures/`；不需要同步时加 `--no-fixtures`。

**方式 C — 开发占位图（仅测试/CI，非实机）**

```powershell
python tests/fixtures/generate_star_rail.py
```

会生成 `tests/fixtures/star_rail/` 并同步到 `configs/games/star_rail/assets/ui/`。

### 2.4 标定 threshold

```powershell
# 在线：从游戏窗口截屏
ocr4game-threshold --game star_rail --anchor claim_button --sweep

# 离线：用静态帧（调试）
ocr4game-threshold --game star_rail --anchor claim_button `
  --frame tests/fixtures/star_rail/frames/daily_panel.png --sweep

# 写回 profile.yaml
ocr4game-threshold --game star_rail --anchor claim_button --apply
```

### 2.5 窗口预检

```powershell
# 列出候选窗口（排查误绑，无需 --name）
ocr4game-annotate --game star_rail --list-windows

# 完整预检
ocr4game --dry-run --game star_rail
```

包含：离线校验 + 查找游戏窗口 + 分辨率提示。日志中应出现 `process=StarRail.exe`、`client_size=(1280, 720)`。

### 2.6 运行日常

```powershell
ocr4game --game star_rail --task daily
```

临时改参数（不改 YAML）：

```powershell
ocr4game --game star_rail --task daily --var sweep_times=3 --var claim_loop_max=5
```

---

## 3. 日常开发与调试

### 3.1 改流程

编辑 `configs/games/star_rail/tasks/daily.yaml`：

- 调整步骤顺序、`when` 分支、`loop` / `repeat`
- 修改 `vars` 块中的默认值
- 详见 [WORKFLOW.md](WORKFLOW.md)

改完后：

```powershell
ocr4game --validate --game star_rail --task daily
```

### 3.2 调试技巧

| 场景 | 做法 |
|------|------|
| 某步总失败 | 该动作加 `optional: true`，先跑通后续 |
| 模板偶发找不到 | `ocr4game-threshold … --apply`、缩小 ROI，或在锚点中配置 `scales` / `match_mode` |
| 看失败画面 | 查看 `runs/star_rail_<时间戳>/fail_<step_id>.png` |
| 详细日志 | `ocr4game --log-level DEBUG …` |
| 步骤被跳过 | 检查步骤 `when` 条件是否不满足 |

### 3.3 星穹铁道锚点一览

| 锚点 | 用途 |
|------|------|
| `main_menu_marker` | 主界面 |
| `guide_entrance` | 开拓指南入口 |
| `daily_panel_marker` | 日常面板 |
| `daily_text` | OCR「日常」等文字 |
| `claim_button` | 领取 |
| `confirm_button` | 确认 |
| `sweep_button` | 扫荡 |
| `dialog_close` | 关弹窗 |

定义见 `configs/games/star_rail/profile.yaml`。

### 3.4 模板锚点匹配参数

`profile.yaml` 中 template 锚点支持轻量多尺度和预处理模式：

```yaml
claim_button:
  type: template
  image: ui/claim_button.png
  threshold: 0.88
  scales: [0.95, 1.0, 1.05]
  match_mode: gray
  roi: [0.3, 0.5, 0.7, 0.95]
```

- `scales`：按多个缩放比例搜索模板，适合窗口缩放或 UI 尺寸轻微变化。
- `match_mode`：`gray`（默认，抗亮度变化）、`color`（保留颜色）、`edges`（更关注轮廓）。
- `roi`：尽量框小，可减少误匹配并提升速度。

---

## 4. 测试

```powershell
pytest                                    # 全部单元测试
pytest tests/test_fixture_regression.py   # 锚点静态图回归
ocr4game --validate --strict --game star_rail --task daily
```

---

## 5. 目录速查

```text
configs/global.yaml                 # 日志、超时、runs 目录
configs/games/star_rail/
  profile.yaml                      # 窗口、分辨率、锚点
  tasks/daily.yaml                  # 日常工作流
  assets/ui/*.png                   # 模板图
runs/                               # 失败截图（gitignore）
tests/fixtures/star_rail/           # 回归用帧图与模板
```

---

## 6. 进一步阅读

- 命令参数：[CLI.md](CLI.md)
- 工作流语法：[WORKFLOW.md](WORKFLOW.md)
- 配置字段：[configs/README.md](../configs/README.md)
- 报错排查：[TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- 新游戏：[ADDING_A_GAME.md](ADDING_A_GAME.md)

---

## 免责声明

本工具仅供学习与研究。自动化可能违反游戏用户协议并带来账号风险，请自行评估。
