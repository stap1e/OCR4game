# 接入新游戏

完整使用流程见 [USAGE.md](USAGE.md)。本文仅描述 **新游戏插件** 步骤。

## 1. 复制配置脚手架

```powershell
Copy-Item -Recurse configs\games\_template configs\games\my_game
```

编辑 `configs/games/my_game/profile.yaml`：

- `game_id` → `my_game`（与目录名一致）
- `window.title_contains` → 窗口标题子串
- `resolution` → 实际客户区宽高

## 2. 实现插件

`src/ocr4game/games/my_game/plugin.py`：

```python
from ocr4game.games.base import GamePlugin
from ocr4game.workflow.context import RunContext

class MyGamePlugin(GamePlugin):
    game_id = "my_game"
    display_name = "我的游戏"

    def preflight(self, ctx: RunContext) -> bool:
        return True
```

添加 `src/ocr4game/games/my_game/__init__.py` 导出该类。

## 3. 注册（entry_points）

`pyproject.toml`：

```toml
[project.entry-points."ocr4game.plugins"]
my_game = "ocr4game.games.my_game.plugin:MyGamePlugin"
```

```powershell
pip install -e ".[dev]"
ocr4game --list-games
```

## 4. 准备模板与任务

```powershell
ocr4game-annotate --game my_game --name example_button
ocr4game-threshold --game my_game --anchor example_button --apply
# 或：ocr4game-import --game my_game --from-dir D:\captures\my_game
```

编辑 `configs/games/my_game/tasks/example.yaml`，参考 [WORKFLOW.md](WORKFLOW.md)。

## 5. 验证

```powershell
ocr4game --validate --game my_game --task example
ocr4game --dry-run --game my_game
ocr4game --game my_game --task example
pytest
```

## 可选：自定义动作

```python
def register_actions(self, registry: ActionRegistry) -> None:
    registry.register("open_map", self._open_map)
```

## 检查清单

- [ ] `game_id` 与目录名、entry_point 一致
- [ ] `profile.yaml` 锚点 PNG 已在 `assets/ui/`
- [ ] `--validate` / `--dry-run` 通过
- [ ] 关键路径有 fixture 或单元测试（推荐）
