# 接入新游戏

## 1. 复制配置脚手架

```powershell
Copy-Item -Recurse configs\games\_template configs\games\my_game
```

编辑 `configs/games/my_game/profile.yaml`：

- `game_id` 改为 `my_game`
- `window.title_contains` 填入窗口标题子串
- `resolution` 按实际客户区分辨率设置

## 2. 实现插件

创建 `src/ocr4game/games/my_game/plugin.py`：

```python
from ocr4game.games.base import GamePlugin
from ocr4game.workflow.context import RunContext

class MyGamePlugin(GamePlugin):
    game_id = "my_game"

    def preflight(self, ctx: RunContext) -> bool:
        # 可选：分辨率硬校验、版本检测等
        return True
```

并添加 `src/ocr4game/games/my_game/__init__.py` 导出该类。

## 3. 注册插件

在 `src/ocr4game/games/registry.py` 的 `_REGISTRY` 中增加：

```python
"my_game": PluginSpec(game_id="my_game", plugin_cls=MyGamePlugin),
```

## 4. 标注 UI 模板

窗口化启动游戏后：

```powershell
ocr4game-annotate --game my_game --name main_menu_marker
```

重复截取所需按钮/图标，然后在 `tasks/example.yaml` 中引用锚点名。

## 5. 编写任务并验证

```powershell
ocr4game --game my_game --dry-run
ocr4game --game my_game --task example
pytest
```

## 可选：游戏特有动作

在 Plugin 中重写 `register_actions()`：

```python
def register_actions(self, registry: ActionRegistry) -> None:
    registry.register("open_map", self._open_map)

def _open_map(self, ctx: RunContext, step_id: str, params) -> bool:
    ...
```

## 检查清单

- [ ] `profile.yaml` 中 `game_id` 与目录名、registry 键一致
- [ ] 所有 template 锚点 PNG 已放入 `assets/ui/`
- [ ] `ocr4game --dry-run` 能找到窗口
- [ ] 关键步骤在 `tests/` 有用 mock 或 fixture 覆盖（推荐）
