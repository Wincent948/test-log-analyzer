"""失败分类与分派表：全项目唯一的定义处。

分派规则是假设，需要和领域专家（Function 团队负责人）确认后再上线。
"""
from __future__ import annotations

CATEGORIES = ("TIMEOUT", "COMMUNICATION", "WATCHDOG_RESET", "VOLTAGE", "FIXTURE", "ASSERTION", "UNKNOWN")

LABEL_ZH = {
    "TIMEOUT": "超时",
    "COMMUNICATION": "通信错误",
    "WATCHDOG_RESET": "看门狗复位",
    "VOLTAGE": "电压异常",
    "FIXTURE": "夹具故障",
    "ASSERTION": "断言失败",
    "UNKNOWN": "无法判断",
}

OWNER = {
    "TIMEOUT": "嵌入式软件",
    "COMMUNICATION": "嵌入式软件",
    "WATCHDOG_RESET": "嵌入式软件",
    "VOLTAGE": "硬件",
    "FIXTURE": "测试工程师",
    "ASSERTION": "待人工确认",
    "UNKNOWN": "待人工确认",
}

# 这两类本身就分不清该找谁，无论规则还是 LLM 判出来，都要人工确认
ALWAYS_REVIEW = {"ASSERTION", "UNKNOWN"}
