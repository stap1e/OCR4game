# OCR4game

基于 **模板匹配 + OCR + YAML 工作流** 的游戏视觉自动化框架。第一版目标：**崩坏：星穹铁道**（窗口模式，客户区约 2048×1152）。

## 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

ocr4game --validate --game star_rail --task daily
ocr4game-annotate --game star_rail --name claim_button
ocr4game --dry-run --game star_rail
ocr4game --game star_rail --task daily
```

完整步骤（安装 → 模板 → 阈值 → 运行 → 调试）见 **[docs/USAGE.md](docs/USAGE.md)**。

## 命令一览

| 命令 | 说明 |
|------|------|
| `ocr4game` | 运行任务（`--validate` / `--dry-run` / `--var`） |
| `ocr4game-annotate` | 框选 UI，保存模板到 `assets/ui/` |
| `ocr4game-threshold` | 标定 template 阈值（`--apply` 写回 profile） |
| `ocr4game-import` | 批量导入截图到 assets 与 fixtures |

参数与退出码：[docs/CLI.md](docs/CLI.md)

## 文档

| 文档 | 内容 |
|------|------|
| [docs/USAGE.md](docs/USAGE.md) | **使用指南**（推荐首读） |
| [docs/WORKFLOW.md](docs/WORKFLOW.md) | 任务 YAML、vars、when/if |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | 常见问题 |
| [docs/ADDING_A_GAME.md](docs/ADDING_A_GAME.md) | 接入新游戏 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 架构与扩展 |
| [configs/README.md](configs/README.md) | 配置文件字段 |

## 目录结构

```text
configs/          # global.yaml + games/<id>/{profile,tasks,assets}
docs/             # 使用说明与参考
src/ocr4game/     # 引擎、插件、工具
tests/            # 单元测试与 fixtures 回归
runs/             # 运行失败截图（gitignore）
```

## 测试

```powershell
pytest
python tests/fixtures/generate_star_rail.py   # 生成占位模板并同步 assets/ui
```

## 免责声明

本工具仅供学习与研究。使用自动化可能违反游戏用户协议并导致账号风险，请自行评估并遵守相关规定。
