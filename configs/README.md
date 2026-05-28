# 配置目录

```text
configs/
  global.yaml              # 全局：日志、runs 目录、截屏/输入/工作流默认值
  games/
    _template/             # 新游戏脚手架（复制后改名，不要直接运行）
    star_rail/             # 崩坏：星穹铁道
      profile.yaml         # 窗口、分辨率、锚点定义
      tasks/*.yaml         # 任务工作流
      assets/ui/           # 模板截图（annotate 工具生成）
```

## global.yaml

| 字段 | 说明 |
|------|------|
| `log_level` | structlog 级别 |
| `runs_dir` | 失败截图与运行产物目录（相对仓库根） |
| `capture.backend` | 截屏后端（当前 `mss`） |
| `capture.fps_limit` | 截屏频率上限（预留） |
| `input.click_jitter` | 点击随机偏移像素 |
| `workflow.default_step_timeout_ms` | `wait_for` 默认超时 |
| `workflow.default_max_retry` | 步骤默认重试次数 |
| `workflow.max_run_minutes` | 单次运行上限（预留） |

## profile.yaml

| 字段 | 说明 |
|------|------|
| `game_id` | 与 `games/<id>/` 目录名、registry 键一致 |
| `window.title_contains` | 窗口标题子串列表 |
| `resolution` | 期望客户区宽高与容差 |
| `paths.assets` / `paths.tasks` | 相对游戏配置目录的子路径 |
| `anchors.<name>` | 模板或 OCR 锚点，供工作流引用 |
| `recovery` | 失败恢复（如 Esc 键） |

### 锚点类型

**template** — 用 PNG 模板匹配：

```yaml
claim_button:
  type: template
  image: ui/claim_button.png
  threshold: 0.88
  roi: [0.3, 0.5, 0.7, 0.95]   # [x0, y0, x1, y1] 相对比例
```

**ocr** — 在 ROI 内查找文字：

```yaml
daily_text:
  type: ocr
  expect: [日常, 每日]
  roi: [0.65, 0.05, 0.98, 0.22]
  min_confidence: 0.5
```

## tasks/*.yaml

```yaml
name: my_task
vars:
  sweep_times: 3
  claim_loop_max: 5
  panel_wait_ms: 1200
steps:
  - id: step_name
    retry: 2
    loop:
      max: "{claim_loop_max}"   # 整值引用，保留 int 类型
    repeat: "{sweep_times}"
    do:
      - wait:
          ms: "{panel_wait_ms}"
      - log: "扫荡 {sweep_times} 次"   # 字符串内部分替换
```

`vars` 通过 `{var_name}` 引用：

- 整段为 `{var}` 时保留原类型（如 int、bool）
- 嵌入字符串时替换为文本；未定义变量会报错

动作完整列表见根目录 [README.md](../README.md)。
