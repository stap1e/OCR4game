# 星穹铁道 UI 资源

将截图模板放在 `ui/` 目录下，文件名与 `profile.yaml` 中 `anchors.*.image` 一致。

推荐流程：

1. 窗口化启动游戏，分辨率宽度约 2048
2. 运行 `ocr4game-annotate --game star_rail`
3. 框选 UI 元素，自动保存 PNG 并更新 `profile.yaml`

占位文件（需替换为真实截图）：

- `main_menu_marker.png` — 主界面特征（如左上角图标/菜单条）
- `claim_button.png` — 「领取」类按钮
