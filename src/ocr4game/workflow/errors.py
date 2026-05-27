from __future__ import annotations


class StepFailed(Exception):
    def __init__(self, step_id: str, message: str = "") -> None:
        self.step_id = step_id
        super().__init__(message or f"步骤失败: {step_id}")
