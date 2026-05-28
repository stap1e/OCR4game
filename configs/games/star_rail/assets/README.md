# 星穹铁道 UI 资源

将截图模板放在 `ui/` 目录下，文件名与 `profile.yaml` 中 `anchors.*.image` 一致。

推荐流程：

1. 窗口化启动游戏，分辨率宽度约 2048
2. 运行 `ocr4game-annotate --game star_rail`
3. 框选 UI 元素，自动保存 PNG 并更新 `profile.yaml`

占位文件（需替换为真实截图，或用 tests/fixtures/star_rail/templates/ 作参考）：

- `main_menu_marker.png` — 主界面左上角特征
- `guide_entrance.png` — 开拓指南/活动入口
- `daily_panel_marker.png` — 日常面板标题栏
- `claim_button.png` — 「领取」类按钮
- `confirm_button.png` — 确认/完成
- `sweep_button.png` — 扫荡/再次挑战
- `dialog_close.png` — 弹窗关闭
