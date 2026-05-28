# 测试 Fixtures

合成截图用于 **锚点回归测试**，无需启动游戏。

## 目录

```text
fixtures/
  generate_star_rail.py   # 重新生成合成 PNG 与 manifest
  star_rail/
    manifest.yaml         # 用例清单（帧、模板、ROI、期望结果）
    frames/               # 模拟游戏画面
    templates/            # 对应锚点模板
```

## 运行回归测试

```powershell
pytest tests/test_fixture_regression.py -q
```

## 替换为真实截图

1. 将游戏内截图放入 `star_rail/frames/`（建议统一缩放到 manifest 中的 `frame_size`）
2. 用 `ocr4game-annotate` 截取对应模板到 `star_rail/templates/`，或从截图裁剪
3. 更新 `star_rail/manifest.yaml` 中的 `roi`、`threshold`、`expect_found`
4. 同步更新 `configs/games/star_rail/profile.yaml` 中的锚点定义

## 重新生成合成数据

修改 `generate_star_rail.py` 后：

```powershell
python tests/fixtures/generate_star_rail.py
```
