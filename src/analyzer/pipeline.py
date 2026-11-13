"""固定流程：规则优先 → LLM 兜底 → 补上分派和人工审核标记。不是 Agent，每一步都由代码决定。"""
from __future__ import annotations

from dataclasses import dataclass

from analyzer import rules
from analyzer.llm import LLMClassifier
from analyzer.parser import Record
from analyzer.taxonomy import ALWAYS_REVIEW, OWNER


@dataclass
class Result:
    record: Record
    category: str
    owner: str
    method: str          # rule / llm / mock / fallback
    detail: str          # 规则名，或 LLM 给的理由
    confidence: float
    needs_review: bool


def classify_record(r: Record, llm: LLMClassifier, streak_ids: set[str] | None = None) -> Result:
    hit = rules.classify(r, streak_ids)
    if hit:
        category, rule_name = hit
        return Result(r, category, OWNER[category], "rule", rule_name, 1.0, category in ALWAYS_REVIEW)
    context = f"module={r.module}, test={r.test_name}, station={r.station}"
    out = llm.classify(r.message, context)
    return Result(r, out.category, OWNER[out.category], out.mode, out.reason, out.confidence,
                  out.needs_review or out.category in ALWAYS_REVIEW)


def analyze(records: list[Record], llm: LLMClassifier | None = None) -> list[Result]:
    llm = llm or LLMClassifier()
    streak_ids = rules.station_streaks(records)
    return [classify_record(r, llm, streak_ids) for r in records if r.failed]
