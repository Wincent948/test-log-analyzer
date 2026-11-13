"""规则分类：能确定的都在这里判断，不用 LLM。

优先级（从高到低）：
1. 夹具：同一测试台连续失败 ≥ FIXTURE_STREAK 次 → FIXTURE
   （不同产品在同一台设备上接连失败、症状各不相同，更可能是设备问题。这是假设，需专家确认）
2. 测量值：单位是 V 且超出上下限 → VOLTAGE
3. 日志文字关键词（PATTERNS 按顺序匹配）
认不出 → 返回 None，交给 LLM。
"""
from __future__ import annotations

import re

from analyzer.parser import Record

FIXTURE_STREAK = 3

# v2（见 docs/ITERATION_LOG.md）：只根据 dev 集的失败案例补充「意思明确」的同义写法。
# 「意外重启」这类可能有多种原因的写法，故意不写成规则，交给 LLM + 人工确认。
PATTERNS: list[tuple[str, str, re.Pattern]] = [
    ("FIXTURE", "fixture_keyword", re.compile(r"fixture|probe|pogo|\bjig\b|夹具|探针", re.I)),
    ("WATCHDOG_RESET", "watchdog", re.compile(r"\bWDT\b|watchdog|看门狗", re.I)),
    ("COMMUNICATION", "bus_error",
     re.compile(r"\bNACK\b|\bCRC\b|\b(no|missing)\s+ACK\b|did not acknowledge|not acknowledged", re.I)),
    ("TIMEOUT", "timeout", re.compile(r"time(d)?[\s-]?out|超时", re.I)),
    ("VOLTAGE", "voltage_keyword", re.compile(r"\bVCC\b|brown[\s-]?out|(under|over)[\s-]?voltage|欠压|过压", re.I)),
    ("ASSERTION", "assertion", re.compile(r"assert", re.I)),
]


def voltage_out_of_range(r: Record) -> bool:
    if r.unit.upper() != "V" or r.measured is None:
        return False
    lo = r.lower_limit if r.lower_limit is not None else float("-inf")
    hi = r.upper_limit if r.upper_limit is not None else float("inf")
    return not (lo <= r.measured <= hi)


def match_message(message: str) -> tuple[str, str] | None:
    for category, rule_name, pattern in PATTERNS:
        if pattern.search(message or ""):
            return category, rule_name
    return None


def station_streaks(records: list[Record], n: int = FIXTURE_STREAK) -> set[str]:
    """返回属于「同一测试台连续失败 ≥ n 次」的 test_id（records 需按时间排序）。"""
    flagged: set[str] = set()
    runs: dict[str, list[str]] = {}
    for r in records:
        run = runs.setdefault(r.station, [])
        if r.failed:
            run.append(r.test_id)
            if len(run) >= n:
                flagged.update(run)
        else:
            run.clear()
    return flagged


def classify(r: Record, streak_ids: set[str] | None = None) -> tuple[str, str] | None:
    """返回 (分类, 命中的规则名)；规则认不出返回 None。"""
    if streak_ids and r.test_id in streak_ids:
        return "FIXTURE", "station_streak"
    if voltage_out_of_range(r):
        return "VOLTAGE", "measured_out_of_range"
    return match_message(r.message)
