# 配置目录

配置说明是 [USAGE.md](../docs/USAGE.md) 的补充，字段级参考见下文。

```text
configs/
  global.yaml              # 全局：日志、runs、超时、输入
  games/
    _template/             # 新游戏脚手架（勿直接运行）
    star_rail/
      profile.yaml         # 窗口、分辨率、锚点
      tasks/*.yaml         # 工作流
      assets/ui/           # 模板 PNG
```

## global.yaml

| 字段 | 说明 |
|------|------|
| `log_level` | 日志级别（可被 CLI `--log-level` 覆盖） |
| `runs_dir` | 失败截图目录（相对仓库根，默认 `runs`） |
| `capture.backend` | 截屏后端（当前 `mss`） |
| `capture.fps_limit` | 截屏频率上限（预留） |
| `input.click_jitter` | 点击随机偏移像素 |
| `input.default_delay_ms` | 输入默认间隔（预留） |
| `workflow.default_step_timeout_ms` | `wait_for` 默认超时（毫秒） |
| `workflow.default_max_retry` | 步骤默认重试次数 |
| `workflow.max_run_minutes` | 单次运行最长时间（分钟），超时退出码 2 |

## profile.yaml

| 字段 | 说明 |
|------|------|
| `game_id` | 与 `games/<id>/` 目录名、插件 `game_id` 一致 |
| `display_name` | 显示名（可选） |
| `window.title_contains` | 窗口标题子串列表 |
| `window.title_exclude` | 排除误匹配的标题子串（如 IDE、终端） |
| `window.process_names` | 仅匹配这些 **exe 文件名**（如 `StarRail.exe`；不是 PID） |

### 星穹铁道（star_rail）窗口字段示例

```yaml
window:
  title_contains:
    - 崩坏：星穹铁道
  process_names:
    - StarRail.exe   # 属性 → 文件名，非任务管理器里的「Star Rail」显示名
  title_exclude:
    - Cursor
    - PowerShell
resolution:
  width: 1280
  height: 720
```

查 exe 名：任务管理器 → 应用 **Star Rail** → 右键 **属性** → **StarRail.exe**。详见 [USAGE.md §2.1.1](../docs/USAGE.md#211-确认窗口与进程名profileyaml)。

| `resolution.width/height/tolerance` | 期望客户区与容差（也用于窗口优选） |
| `paths.assets` / `paths.tasks` | 相对游戏目录的子路径 |
| `anchors.<name>` | 模板或 OCR 锚点 |
| `recovery.escape_key` | 失败时尝试按下的键 |

### 锚点类型

**template** — PNG 模板匹配：

```yaml
claim_button:
  type: template
  image: ui/claim_button.png
  threshold: 0.88
  roi: [0.3, 0.5, 0.7, 0.95]   # [x0,y0,x1,y1] 相对比例 0~1
```

**ocr** — ROI 内文字识别：

```yaml
daily_text:
  type: ocr
  expect: [日常, 每日, 活跃度]
  roi: [0.65, 0.05, 0.98, 0.22]
  min_confidence: 0.5
```

模板获取：`ocr4game-annotate` / `ocr4game-import`（见 [assets/README.md](games/star_rail/assets/README.md)）。

## tasks/*.yaml

```yaml
name: my_task
vars:
  sweep_times: 1
steps:
  - id: step_name
    when:                          # 可选，false 则跳过整步
      anchor_visible: claim_button
    retry: 2
    loop:
      max: "{claim_loop_max}"
    repeat: "{sweep_times}"
    do:
      - if:                        # 可选，动作级分支
          when:
            var_gt: { sweep_times: 0 }
          do:
            - log: "开始扫荡"
      - click_template:
          anchor: claim_button
          optional: true
```

- **vars / `{var}` / `--var`**：见 [WORKFLOW.md](../docs/WORKFLOW.md)
- **when / if / 动作列表**：见 [WORKFLOW.md](../docs/WORKFLOW.md)
- **校验**：`ocr4game --validate --game star_rail --task daily`
