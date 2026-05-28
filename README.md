# OCR4game

基于 **模板匹配 + OCR + YAML 工作流** 的游戏视觉自动化框架。第一版目标游戏：**崩坏：星穹铁道**（窗口模式，分辨率约 2048×1152）。

## 环境要求

- Windows 10/11
- Python 3.11+
- 游戏 **窗口化** 运行，客户区宽度约 **2048**（高度可在 `profile.yaml` 中调整）

## 快速开始

```powershell
cd c:\Users\16025\PythonProjects\OCR4game
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

1. 启动《崩坏：星穹铁道》并切到窗口模式  
2. 查看已注册/已配置游戏：

```powershell
ocr4game --list-games
```

3. 预检（只检查能否找到窗口）：

```powershell
ocr4game --game star_rail --dry-run
```

4. 用标注工具截取 UI 模板（例：领取按钮）：

```powershell
ocr4game-annotate --game star_rail --name claim_button
```

在弹出窗口中 **拖拽框选** 目标 UI，`Enter` 确认。会自动保存 PNG 并写入 `configs/games/star_rail/profile.yaml`。

5. 编辑日常流程：`configs/games/star_rail/tasks/daily.yaml`

6. 运行日常（需已配置好模板）：

```powershell
ocr4game --game star_rail --task daily
```

失败截图保存在 `runs/` 目录。

## 目录结构

```text
configs/
  global.yaml                 # 全局配置（见 configs/README.md）
  games/
    _template/                # 新游戏脚手架
    star_rail/
      profile.yaml            # 窗口、分辨率、锚点
      tasks/daily.yaml        # 日常工作流
      assets/ui/              # 模板截图
docs/
  ARCHITECTURE.md             # 分层架构与数据流
  ADDING_A_GAME.md            # 接入新游戏指南
src/ocr4game/
  app.py                      # CLI 入口
  config.py                   # Pydantic 配置模型
  resources.py                # 路径解析
  runtime/binding.py          # 窗口/截屏/输入绑定
  platform/                   # 窗口、截屏、输入
  perception/                 # 模板、OCR、融合
  workflow/
    engine.py                 # YAML 工作流引擎
    actions/                  # 可扩展动作注册表
    context.py                # 单次运行上下文
  games/
    registry.py               # 插件注册与发现
    star_rail/                # 星穹铁道插件
  tools/annotate.py           # 框选标注工具
tests/                        # 单元测试（无需启动游戏）
runs/                         # 运行产物（gitignore）
```

## 工作流动作（节选）

| 动作 | 说明 |
|------|------|
| `assert_window` | 确认游戏窗口已绑定 |
| `wait` | 等待毫秒 |
| `wait_for` | 等待某锚点出现 |
| `click_template` | 点击模板锚点 |
| `click_ocr` | 点击 OCR 匹配文字中心 |
| `log` | 输出日志 |

步骤可加 `optional: true` 跳过失败（模板未就绪时便于调试）。  
配置字段说明见 [configs/README.md](configs/README.md)。

## 接入新游戏

复制 `configs/games/_template/` → 实现 Plugin → 注册到 `games/registry.py`。  
详细步骤见 [docs/ADDING_A_GAME.md](docs/ADDING_A_GAME.md)。

## 分辨率说明

`profile.yaml` 默认：

```yaml
resolution:
  width: 2048
  height: 1152
  tolerance: 32
```

若你实际是 2048×1536 等比例，请改 `height` 后重新用 `annotate` 截模板。

## 测试

```powershell
pytest
pytest tests/test_fixture_regression.py -q   # 锚点静态图回归
```

合成 fixture 位于 `tests/fixtures/star_rail/`，可用 `python tests/fixtures/generate_star_rail.py` 重新生成。

## 免责声明

本工具仅供学习与研究。使用自动化可能违反游戏用户协议并导致账号风险，请自行评估并遵守相关规定。
