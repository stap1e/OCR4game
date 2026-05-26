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
2. 预检（只检查能否找到窗口）：

```powershell
ocr4game --game star_rail --dry-run
```

3. 用标注工具截取 UI 模板（例：领取按钮）：

```powershell
ocr4game-annotate --game star_rail --name claim_button
```

在弹出窗口中 **拖拽框选** 目标 UI，`Enter` 确认。会自动保存 PNG 并写入 `configs/games/star_rail/profile.yaml`。

4. 编辑日常流程：`configs/games/star_rail/tasks/daily.yaml`

5. 运行日常（需已配置好模板）：

```powershell
ocr4game --game star_rail --task daily
```

失败截图保存在 `runs/` 目录。

## 目录结构

```text
configs/
  global.yaml                 # 全局配置
  games/star_rail/
    profile.yaml              # 窗口标题、分辨率、锚点
    tasks/daily.yaml          # 日常工作流
    assets/ui/                # 你截取的模板图
src/ocr4game/
  platform/                   # 窗口、截屏、输入
  perception/                 # 模板、OCR、融合
  workflow/                   # YAML 引擎
  games/star_rail/            # 星穹铁道插件
  tools/annotate.py           # 框选标注工具
tests/                        # 单元测试（无需启动游戏）
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
```

## 免责声明

本工具仅供学习与研究。使用自动化可能违反游戏用户协议并导致账号风险，请自行评估并遵守相关规定。
