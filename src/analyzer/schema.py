"""LLM 输出的格式护栏：字段、类型、取值范围、只能是固定分类。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["TIMEOUT", "COMMUNICATION", "WATCHDOG_RESET", "VOLTAGE", "FIXTURE", "ASSERTION", "UNKNOWN"]


class Classification(BaseModel):
    category: Category                       # 不在 7 类里（LLM 自己编的）→ 校验失败
    reason: str = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)    # 必须是 0~1 的小数
