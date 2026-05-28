# 常见问题排查

## 安装与命令

### `ocr4game` 不是内部或外部命令

未安装或未激活虚拟环境：

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

或临时使用：

```powershell
$env:PYTHONPATH="src"
python -m ocr4game.app --list-games
```

### `ModuleNotFoundError: win32gui`

未安装依赖或未在 venv 中：

```powershell
pip install -e ".[dev]"
```

离线命令（`--validate`、`ocr4game-threshold --frame …`）不需要 Win32。

---

## 窗口与分辨率

### 预检失败 / 未找到游戏窗口

1. 确认游戏 **窗口化** 已启动且在前台
2. 检查 `profile.yaml` → `window.title_contains` 是否包含当前窗口标题子串
3. 运行 `ocr4game --dry-run --log-level DEBUG`

### 分辨率与配置不一致（warning）

日志出现 `客户区分辨率与配置不一致`：

1. 查看日志中的 `actual` 与 `expected`
2. 修改 `configs/games/star_rail/profile.yaml` → `resolution.height`（或 width）
3. **重新** `ocr4game-annotate` 截取模板（分辨率变了必须重截）

---

## 模板与识别

### 模板匹配失败 / 未找到锚点

1. 确认 `assets/ui/` 下 PNG 存在：`ocr4game --validate --strict`
2. 用 `ocr4game-threshold --anchor … --sweep` 看置信度
3. 阈值过高 → `--apply` 降低，或重新 annotate
4. ROI 不准 → 重新 annotate（会自动写 ROI）
5. 占位 fixture 模板在 **2048 实机** 上通常无效，必须实机 annotate

### OCR 找不到「日常」等文字

1. 调整 `profile.yaml` 中 `daily_text.roi` 覆盖文字区域
2. 增加 `expect` 关键词列表
3. 适当降低 `min_confidence`

---

## 工作流

### 步骤被跳过（when=false）

步骤配置了 `when:`，当前画面不满足条件。检查：

- 是否已在目标界面（锚点 visible/missing）
- `vars` 是否如预期（`--var` 覆盖或 YAML 中 `vars` 块）

### 任务很快结束但没做事

大量步骤带 `optional: true`，失败被静默跳过。逐步去掉 optional，或看 DEBUG 日志。

### 任务超时（退出码 2）

`global.yaml` → `workflow.max_run_minutes` 超限。可临时调大或优化 `wait_for` 超时。

### 未知动作 / 未定义锚点

```powershell
ocr4game --validate --game star_rail --task daily
```

修正 YAML 中拼写错误的动作名或锚点名。

---

## 校验

| 命令 | 用途 |
|------|------|
| `--validate` | 离线查 YAML、锚点、模板 |
| `--validate --strict` | 缺 PNG 也报错 |
| `--dry-run` | 校验 + 窗口预检 |

---

## 仍无法解决

1. 保留 `runs/` 下失败截图
2. 用 `--log-level DEBUG` 重跑
3. 检查 [WORKFLOW.md](WORKFLOW.md) 中 `when` / `optional` 语义
