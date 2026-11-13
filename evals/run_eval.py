"""评测：用带标准答案的失败日志，衡量分类准不准。

python evals/run_eval.py                    # dev + test，有 key 就调用 LLM
python evals/run_eval.py --split dev        # 调规则 / 提示词时只看 dev
python evals/run_eval.py --no-llm           # mock 模式（CI 用）
python evals/run_eval.py --no-llm --min-rule-precision 1.0   # 规则判错一条就返回非 0（回归门槛）

指标：
- 准确率：分类 = 标准答案 的比例
- 规则覆盖率：被规则处理的比例；规则精确率：规则处理的里面判对的比例（规则只能少判，不能判错）
- LLM 准确率：交给 LLM 的里面判对的比例（mock 模式下不计算）
输出：evals/results.md、evals/results.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from analyzer.llm import LLMClassifier  # noqa: E402
from analyzer.parser import Record  # noqa: E402
from analyzer.pipeline import classify_record  # noqa: E402
from analyzer.taxonomy import LABEL_ZH  # noqa: E402

CASES = ROOT / "evals" / "cases.jsonl"


def ratio(a: int, b: int) -> float | None:
    return round(a / b, 3) if b else None


def pct(x: float | None) -> str:
    return "—" if x is None else f"{x:.0%}"


def metrics(rows: list[dict]) -> dict:
    rule = [r for r in rows if r["method"] == "rule"]
    llm = [r for r in rows if r["method"] in ("llm", "fallback")]
    return {
        "n": len(rows),
        "accuracy": ratio(sum(r["correct"] for r in rows), len(rows)),
        "rule_coverage": ratio(len(rule), len(rows)),
        "rule_precision": ratio(sum(r["correct"] for r in rule), len(rule)),
        "llm_accuracy": ratio(sum(r["correct"] for r in llm), len(llm)),
        "mock": sum(r["method"] == "mock" for r in rows),
        "needs_review": sum(r["needs_review"] for r in rows),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="all", choices=["all", "dev", "test"])
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--min-rule-precision", type=float, default=None)
    a = ap.parse_args(argv)

    llm = LLMClassifier()
    if a.no_llm:
        llm.client = None
    cases = [json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()]
    if a.split != "all":
        cases = [c for c in cases if c["split"] == a.split]

    rows = []
    for c in cases:
        rec = Record("2026-11-13 09:00:00", c["id"], "eval", c["module"], "EVAL", "FAIL", c["message"])
        res = classify_record(rec, llm)
        rows.append({**c, "got": res.category, "method": res.method, "detail": res.detail,
                     "confidence": res.confidence, "needs_review": res.needs_review,
                     "correct": res.category == c["expected"]})

    splits = {s: metrics([r for r in rows if r["split"] == s]) for s in ("dev", "test") if any(r["split"] == s for r in rows)}
    mode = "mock（未调用 LLM）" if llm.offline else f"LLM：{llm.model}"

    L = [f"# 评测结果\n\n- 模式：{mode}\n- 题数：{len(rows)}\n",
         "| 集合 | 题数 | 准确率 | 规则覆盖率 | 规则精确率 | LLM 准确率 | mock 未判 | 需人工确认 |",
         "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for s, m in splits.items():
        L.append(f"| {s} | {m['n']} | {pct(m['accuracy'])} | {pct(m['rule_coverage'])} | {pct(m['rule_precision'])} | "
                 f"{pct(m['llm_accuracy'])} | {m['mock']} | {m['needs_review']} |")
    wrong = [r for r in rows if not r["correct"]]
    L += ["", f"## 判错 / 未判出（{len(wrong)} 条）", "",
          "| id | 集合 | 日志 | 期望 | 实际 | 判断方式 |", "| --- | --- | --- | --- | --- | --- |"]
    L += [f"| {r['id']} | {r['split']} | {r['message']} | {LABEL_ZH[r['expected']]} | {LABEL_ZH[r['got']]} | {r['method']} |"
          for r in wrong]
    (ROOT / "evals" / "results.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (ROOT / "evals" / "results.json").write_text(
        json.dumps({"mode": mode, "splits": splits, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"模式：{mode}")
    for s, m in splits.items():
        print(f"[{s}] 准确率 {pct(m['accuracy'])}  规则覆盖 {pct(m['rule_coverage'])}  规则精确 {pct(m['rule_precision'])}  "
              f"LLM 准确 {pct(m['llm_accuracy'])}  mock 未判 {m['mock']}  需人工 {m['needs_review']}")
    print(f"判错 / 未判出：{[r['id'] for r in wrong]}")

    if a.min_rule_precision is not None:
        rule_rows = [r for r in rows if r["method"] == "rule"]
        prec = ratio(sum(r["correct"] for r in rule_rows), len(rule_rows)) or 0.0
        if prec < a.min_rule_precision:
            print(f"✗ 规则精确率 {prec:.0%} 低于门槛 {a.min_rule_precision:.0%}")
            return 1
        print(f"✓ 规则精确率 {prec:.0%} 达到门槛")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
