# OCR4game

基于 **模板匹配 + OCR + YAML 工作流** 的游戏视觉自动化框架。当前内置示例目标是 **崩坏：星穹铁道**，推荐游戏窗口模式、客户区 **1280×720**。

> 本项目适合学习游戏视觉自动化、模板匹配、OCR 与可配置工作流。实际使用前请自行评估游戏用户协议和账号风险。

## 功能特性

- **模板匹配**：基于 OpenCV，支持 ROI、阈值、灰度/边缘/彩色匹配和轻量多尺度识别。
- **OCR 识别**：基于 RapidOCR，用于文字锚点和界面状态判断。
- **YAML 工作流**：用 `tasks/*.yaml` 描述点击、等待、条件分支、循环和变量覆盖。
- **游戏插件机制**：通过 `entry_points` 注册新游戏插件，核心逻辑可复用。
- **调试工具链**：提供模板框选、阈值标定、截图导入、离线校验、失败截图保存。
- **回归测试 fixtures**：可用合成截图验证模板锚点是否仍可识别。

## 环境要求

- Windows 10/11
- Python **3.11+**（推荐 3.11 或 3.12）
- 游戏窗口化运行；星穹铁道推荐客户区 **1280×720**
- 可选：PowerShell 7 或 Windows PowerShell

说明：`rapidocr-onnxruntime` 在不同 Python 版本上的 wheel 支持可能不同。如果安装 OCR 依赖遇到问题，优先尝试 Python 3.11/3.12。

## 安装

### 1. 克隆或进入项目目录

```powershell
cd C:\Users\16025\PythonProjects\OCR4game
```

### 2. 创建并激活虚拟环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

如果 PowerShell 拦截脚本执行，可临时允许当前会话执行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 3. 安装项目

开发/本地运行推荐安装 dev 依赖：

```powershell
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

只安装运行依赖：

```powershell
pip install -e .
```

### 4. 验证安装

```powershell
ocr4game --version
ocr4game --list-games
```

如果命令不可用，可先确认虚拟环境已激活，或用模块方式运行：

```powershell
python -m ocr4game.app --list-games
```

## 快速开始：跑通星穹铁道 daily

推荐顺序：

```text
安装 → 启动游戏窗口 → 离线校验 → 准备模板 → 标定阈值 → 窗口预检 → 运行任务
```

### 1. 启动游戏并确认窗口

- 使用窗口模式，不要最小化。
- 客户区分辨率尽量与 `configs/games/star_rail/profile.yaml` 中的 `resolution` 一致。
- 默认配置会匹配窗口标题和进程名 `StarRail.exe`。

列出候选窗口：

```powershell
ocr4game-annotate --game star_rail --list-windows --verbose
```

期望看到类似信息：

```text
process=StarRail.exe size=1280x720 ... <-- 已选
```

### 2. 离线校验配置和任务

无需打开游戏：

```powershell
ocr4game --validate --game star_rail --task daily
```

严格校验会把缺失模板等资源问题视为失败：

```powershell
ocr4game --validate --strict --game star_rail --task daily
```

### 3. 准备 UI 模板

#### 方式 A：游戏内框选模板（推荐）

```powershell
ocr4game-annotate --game star_rail --name main_menu_marker
ocr4game-annotate --game star_rail --name claim_button
ocr4game-annotate --game star_rail --name confirm_button
```

操作方式：弹出窗口后拖拽框选 UI，按 `Enter` 保存，按 `Esc` 取消。工具会自动：

- 保存模板到 `configs/games/star_rail/assets/ui/`
- 更新 `configs/games/star_rail/profile.yaml` 中对应锚点的 `roi`

#### 方式 B：批量导入已有截图

```powershell
ocr4game-import --game star_rail --from-dir D:\captures\star_rail
```

支持目录结构：

```text
D:\captures\star_rail\
  ui\
    ui\claim_button.png
    ui\buttons\confirm_button.png
  frames\
    daily_panel.png
    nested\debug_frame.jpg
```

说明：

- UI 模板会按 `profile.yaml` 中 `anchors.*.image` 的相对路径导入，支持子目录。
- frames 支持 `.png`、`.jpg`、`.jpeg`、`.webp`。
- 默认会同步到 `tests/fixtures/`；不需要同步时加 `--no-fixtures`。

#### 方式 C：生成测试占位图

仅用于测试/CI，不代表真实游戏界面：

```powershell
python tests/fixtures/generate_star_rail.py
```

### 4. 标定模板阈值

在线从游戏窗口截屏：

```powershell
ocr4game-threshold --game star_rail --anchor claim_button --sweep
```

离线使用静态截图：

```powershell
ocr4game-threshold --game star_rail --anchor claim_button `
  --frame tests/fixtures/star_rail/frames/daily_panel.png --sweep
```

将建议阈值写回 `profile.yaml`：

```powershell
ocr4game-threshold --game star_rail --anchor claim_button --apply
```

### 5. 预检并运行

窗口预检，不执行动作：

```powershell
ocr4game --dry-run --game star_rail --task daily
```

运行 daily：

```powershell
ocr4game --game star_rail --task daily
```

临时覆盖任务变量：

```powershell
ocr4game --game star_rail --task daily --var sweep_times=3 --var claim_loop_max=5
```

提高日志详细程度：

```powershell
ocr4game --log-level DEBUG --game star_rail --task daily
```

## 常用命令

| 命令 | 说明 |
|------|------|
| `ocr4game --list-games` | 列出已注册 / 已配置游戏 |
| `ocr4game --validate --game star_rail --task daily` | 离线校验任务 |
| `ocr4game --dry-run --game star_rail --task daily` | 校验 + 窗口预检 |
| `ocr4game --game star_rail --task daily` | 执行任务 |
| `ocr4game-annotate --game star_rail --name claim_button` | 框选并保存模板 |
| `ocr4game-annotate --game star_rail --list-windows --verbose` | 排查窗口绑定 |
| `ocr4game-threshold --game star_rail --anchor claim_button --sweep` | 查看匹配置信度和阈值档位 |
| `ocr4game-import --game star_rail --from-dir D:\captures\star_rail` | 批量导入模板和 frames |

完整参数与退出码见 [docs/CLI.md](docs/CLI.md)。

## 项目结构

```text
configs/
  global.yaml                         # 日志、捕获、输入、工作流默认配置
  games/star_rail/
    profile.yaml                      # 窗口、分辨率、锚点、模板匹配参数
    tasks/daily.yaml                  # daily 工作流
    assets/ui/*.png                   # 实机模板图
docs/                                 # 使用、CLI、工作流、新游戏和排错文档
src/ocr4game/                         # 引擎、感知、插件、运行时和工具 CLI
tests/                                # 单元测试与 fixtures 回归
runs/                                 # 运行失败截图和日志产物（gitignore）
```

## 配置入口

### 游戏 profile

`configs/games/star_rail/profile.yaml` 定义：

- `window`：窗口标题、排除项、进程名
- `resolution`：期望客户区大小和容差
- `anchors`：模板/OCR 锚点
- `recovery`：失败恢复按键
- `extensions`：插件或游戏自定义扩展配置

模板锚点常见字段：

```yaml
claim_button:
  type: template
  image: ui/claim_button.png
  threshold: 0.88
  scales: [0.95, 1.0, 1.05]
  match_mode: gray
  roi: [0.3, 0.5, 0.7, 0.95]
```

### 任务 YAML

`configs/games/star_rail/tasks/daily.yaml` 描述步骤、条件、循环和变量。更多语法见 [docs/WORKFLOW.md](docs/WORKFLOW.md)。

## 测试与开发

安装 dev 依赖后运行：

```powershell
pytest
python -m ruff check src tests
```

常用定向测试：

```powershell
pytest tests/test_fixture_regression.py -q
pytest tests/test_workflow_engine.py tests/test_validation.py -q
ocr4game --validate --strict --game star_rail --task daily
```

如果当前环境提示 `No module named pytest` 或 `No module named ruff`，说明未安装 dev 依赖：

```powershell
pip install -e ".[dev]"
```

## 新增游戏

新增游戏通常需要：

1. 新建 `configs/games/<game_id>/profile.yaml`
2. 新建 `configs/games/<game_id>/tasks/*.yaml`
3. 准备模板资源 `configs/games/<game_id>/assets/`
4. 可选：实现 `src/ocr4game/games/<game_id>/plugin.py`
5. 在 `pyproject.toml` 注册 entry point

```toml
[project.entry-points."ocr4game.plugins"]
my_game = "ocr4game.games.my_game.plugin:MyGamePlugin"
```

详见 [docs/ADDING_A_GAME.md](docs/ADDING_A_GAME.md)。

## 常见问题

| 问题 | 处理 |
|------|------|
| `ocr4game` 命令不存在 | 激活 `.venv`，或重新执行 `pip install -e ".[dev]"` |
| 找不到游戏窗口 | 确认窗口化、未最小化、`profile.yaml` 的标题/进程名正确 |
| 分辨率不匹配 | 调整游戏客户区到 `profile.yaml` 中的分辨率，或同步修改配置 |
| 模板识别失败 | 重新框选模板、缩小 ROI、运行 `ocr4game-threshold --sweep` 标定阈值 |
| OCR 依赖安装失败 | 尝试 Python 3.11/3.12，并升级 pip |
| 任务中途失败 | 查看 `runs/<game_id>_<timestamp>/fail_<step_id>.png` |

更多排查见 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)。

## 文档索引

| 文档 | 内容 |
|------|------|
| [docs/USAGE.md](docs/USAGE.md) | 从安装到运行的完整流程 |
| [docs/CLI.md](docs/CLI.md) | CLI 参数和退出码 |
| [docs/WORKFLOW.md](docs/WORKFLOW.md) | 工作流 YAML、vars、when/if |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | 常见问题排查 |
| [docs/ADDING_A_GAME.md](docs/ADDING_A_GAME.md) | 接入新游戏 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 架构与扩展点 |
| [configs/README.md](configs/README.md) | 配置字段参考 |

## 免责声明

本工具仅供学习与研究。使用自动化可能违反游戏用户协议并导致账号风险，请自行评估并遵守相关规定。