"""读取与清洗测试日志 CSV，并做基础统计。完全确定性，不用 LLM。"""
from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

REQUIRED = ("timestamp", "test_id", "test_name", "module", "station", "status", "message")


@dataclass
class Record:
    timestamp: str
    test_id: str
    test_name: str
    module: str
    station: str
    status: str
    message: str
    measured: float | None = None
    lower_limit: float | None = None
    upper_limit: float | None = None
    unit: str = ""

    @property
    def failed(self) -> bool:
        return self.status == "FAIL"


def _num(v: str | None) -> float | None:
    """空值或非数字 → None，不让一个坏格子让整个文件读失败。"""
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


def clean_module(v: str | None) -> str:
    """统一小写、去前后空格；空值记为 unknown（大小写不一致会被当成不同模块）。"""
    v = (v or "").strip().lower()
    return v or "unknown"


def load(path: str | Path) -> list[Record]:
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"日志缺少必要字段：{missing}")
        records = []
        for row in reader:
            records.append(Record(
                timestamp=(row["timestamp"] or "").strip(),
                test_id=(row["test_id"] or "").strip(),
                test_name=(row["test_name"] or "").strip(),
                module=clean_module(row["module"]),
                station=(row["station"] or "").strip().upper() or "UNKNOWN",
                status=(row["status"] or "").strip().upper(),
                message=(row["message"] or "").strip(),
                measured=_num(row.get("measured")),
                lower_limit=_num(row.get("lower_limit")),
                upper_limit=_num(row.get("upper_limit")),
                unit=(row.get("unit") or "").strip(),
            ))
    records.sort(key=lambda r: r.timestamp)  # 夹具规则依赖时间顺序
    return records


def summarize(records: list[Record]) -> dict:
    failed = [r for r in records if r.failed]
    return {
        "total": len(records),
        "failed": len(failed),
        "pass_rate": round(1 - len(failed) / len(records), 3) if records else 0.0,
        "fail_by_module": dict(Counter(r.module for r in failed).most_common()),
        "fail_by_station": dict(Counter(r.station for r in failed).most_common()),
    }
