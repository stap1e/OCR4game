from __future__ import annotations


class StepFailed(Exception):
    def __init__(self, step_id: str, message: str = "") -> None:
        self.step_id = step_id
        super().__init__(message or f"步骤失败: {step_id}")


class RunTimeout(StepFailed):
    def __init__(self, *, max_minutes: int) -> None:
        super().__init__("run_timeout", f"任务运行超过 {max_minutes} 分钟上限")
        self.max_minutes = max_minutes
