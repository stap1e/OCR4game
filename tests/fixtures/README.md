# 测试 Fixtures

合成或真实截图，用于 **离线锚点回归**，无需启动游戏。

## 目录

```text
fixtures/
  generate_star_rail.py       # 生成合成 PNG + 同步 assets/ui
  star_rail/
    manifest.yaml             # 回归用例（帧、模板、ROI、期望）
    frames/                   # 模拟/真实游戏画面
    templates/                # 锚点模板
```

## 常用命令

```powershell
python tests/fixtures/generate_star_rail.py              # 生成并同步 assets
pytest tests/test_fixture_regression.py -q                 # 跑回归
ocr4game-import --game star_rail --from-dir D:\captures  # 导入真实图
```

## 替换为真实截图

1. 用 `ocr4game-import` 导入，或手动放入 `frames/`、`templates/`
2. 更新 `manifest.yaml` 的 `roi`、`threshold`、`expect_found`
3. 保持与 `profile.yaml` 锚点定义一致
4. 运行 `pytest tests/test_fixture_regression.py`

详见 [USAGE.md](../docs/USAGE.md) 与 [assets/README.md](../configs/games/star_rail/assets/README.md)。
