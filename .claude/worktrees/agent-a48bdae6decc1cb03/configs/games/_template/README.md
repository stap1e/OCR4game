# 新游戏配置脚手架

复制本目录到 `configs/games/<your_game_id>/`，然后：

1. 将全部 `my_game` 替换为你的 `game_id`
2. 实现并注册 Python 插件（见 docs/ADDING_A_GAME.md）
3. 用 `ocr4game-annotate --game <id> --name <anchor>` 截取 UI

**不要** 在未注册插件的情况下直接运行 `--game my_game`。
