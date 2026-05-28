# 星穹铁道 UI 资源

`assets/ui/` 存放模板 PNG，与 `profile.yaml` 中 `anchors.*.image` 对应。

**完整说明**：[docs/USAGE.md](../../../../docs/USAGE.md) §2.3

## 快速命令

```powershell
# 1. 窗口化启动游戏
ocr4game-annotate --game star_rail --name claim_button

# 2. 标定 threshold
ocr4game-threshold --game star_rail --anchor claim_button --apply

# 3. 或批量导入已有截图目录
ocr4game-import --game star_rail --from-dir D:\screenshots\star_rail
```

导入目录结构：

```text
star_rail/
  ui/
    main_menu_marker.png
    claim_button.png
    ...
  frames/              # 可选，同步到 tests/fixtures/star_rail/frames/
    daily_panel.png
```

## 开发用合成模板

无真实截图时，可从 fixture 同步占位图：

```powershell
python tests/fixtures/generate_star_rail.py
```

会自动写入 `tests/fixtures/star_rail/` 并同步到本目录 `ui/`。

## 锚点列表

- `main_menu_marker.png` — 主界面特征
- `guide_entrance.png` — 开拓指南入口
- `daily_panel_marker.png` — 日常面板标题栏
- `claim_button.png` — 领取按钮
- `confirm_button.png` — 确认
- `sweep_button.png` — 扫荡
- `dialog_close.png` — 关闭弹窗
