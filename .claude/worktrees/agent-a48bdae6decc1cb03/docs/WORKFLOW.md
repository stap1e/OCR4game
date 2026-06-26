# 工作流参考

任务文件位于 `configs/games/<id>/tasks/*.yaml`。引擎按顺序执行 `steps`，每步包含一个或多个 `do` 动作。

## 任务结构

```yaml
name: my_task
description: 说明文字
vars:
  sweep_times: 1
steps:
  - id: step_id
    retry: 2           # 可选，整步重试次数
    repeat: 3          # 固定重复 N 次（忽略动作返回 false）
    loop:              # 最多 N 次，遇 false 提前 break
      max: 5
    do:
      - log: "消息"
      - wait: { ms: 500 }
```

### `repeat` vs `loop`

| 字段 | 行为 |
|------|------|
| `repeat: N` | 固定执行 N 次，**不**因动作返回 `false` 而停止 |
| `loop.max: N` | 最多 N 次，任一动作为 `false` 时 **break** 循环 |

## 变量 `{var}`

`vars` 块定义变量，步骤中用 `{var_name}` 引用：

- 整值 `" {sweep_times} "` → 保留 int/bool 类型
- 字符串内 `"扫荡 {sweep_times} 次"` → 文本替换
- CLI `--var sweep_times=3` 覆盖 YAML 中的同名变量

## 动作一览

| 动作 | 参数 | 说明 |
|------|------|------|
| `assert_window` | `true` | 确认窗口已绑定 |
| `log` | 字符串或 `{msg: "..."}` | 输出日志 |
| `wait` | `{ms: 500}` | 等待毫秒 |
| `wait_for` | `{anchor, timeout_ms?, optional?}` | 轮询直到锚点出现 |
| `click_template` | `{anchor, optional?}` | 点击模板锚点 |
| `click_ocr` | `{anchor, optional?}` | 点击 OCR 锚点文字中心 |

### `optional: true`

动作失败时不中止任务（用于模板尚未就绪时的调试）。

## 步骤级 `when` 与动作级 `if`

**步骤 `when`**：条件为 false 时跳过整步。

```yaml
- id: claim_daily_rewards
  when:
    anchor_visible: claim_button
  do:
    - click_template: { anchor: claim_button }
```

**动作 `if`**：在 `do` 内按条件执行子动作。

```yaml
do:
  - if:
      when:
        var_gt: { sweep_times: 0 }
      do:
        - log: "开始扫荡"
        - click_template: { anchor: sweep_button, optional: true }
```

### 条件表达式

| 键 | 含义 |
|----|------|
| `anchor_visible` | 模板/OCR 锚点当前可见 |
| `anchor_missing` | 锚点不可见 |
| `var_eq` / `var_ne` | 变量等于/不等于 |
| `var_gt` / `var_gte` / `var_lt` / `var_lte` | 变量比较 |
| `all` / `any` | 列表内条件与/或 |
| `not` | 取反 |

```yaml
when:
  all:
    - anchor_missing: daily_panel_marker
    - var_gt: { sweep_times: 0 }
```

## 全局限制

- `global.yaml` → `workflow.max_run_minutes`：单次运行最长时间，超时抛出 `RunTimeout`
- `workflow.default_step_timeout_ms`：`wait_for` 默认超时
- `workflow.default_max_retry`：步骤默认重试次数

## 校验

检查项包括：任务 schema、动作名、锚点引用、vars 解析、模板 PNG（缺文件为 warning，`--strict` 为 error）。步骤 `when` / 动作 `if` 会离线校验锚点名与结构。

```powershell
ocr4game --validate --game star_rail --task daily
```

更多排查见 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)。

## 扩展动作

游戏 Plugin 可通过 `register_actions()` 向注册表追加自定义动作（见 [ADDING_A_GAME.md](ADDING_A_GAME.md)）。
