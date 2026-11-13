"""命令行入口。

python -m analyzer.cli data/logs/sample.csv                     # 打印统计和分类
python -m analyzer.cli data/logs/sample.csv --report reports/report.md
python -m analyzer.cli data/logs/sample.csv --no-llm            # 强制 mock，不调用 LLM
"""
from __future__ import annotations

import argparse
from pathlib import Path

from analyzer import parser, pipeline, report
from analyzer.llm import LLMClassifier
from analyzer.taxonomy import LABEL_ZH


class _Offline(LLMClassifier):
    def __init__(self):
        self.client, self.model = None, ""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="硬件测试日志分析工具")
    ap.add_argument("log", help="测试日志 CSV")
    ap.add_argument("--report", help="输出 Markdown 报告的路径")
    ap.add_argument("--no-llm", action="store_true", help="不调用 LLM（mock 模式）")
    a = ap.parse_args(argv)

    records = parser.load(a.log)
    summary = parser.summarize(records)
    llm = _Offline() if a.no_llm else LLMClassifier()
    results = pipeline.analyze(records, llm)

    print(f"模式：{'mock（未调用 LLM）' if llm.offline else 'LLM：' + llm.model}")
    print(f"总数 {summary['total']}，失败 {summary['failed']}，通过率 {summary['pass_rate']:.1%}")
    print(f"按模块失败：{summary['fail_by_module']}")
    print(f"按测试台失败：{summary['fail_by_station']}")
    for r in results:
        flag = " ⚠️人工确认" if r.needs_review else ""
        print(f"  {r.record.test_id} {LABEL_ZH[r.category]:<6} → {r.owner:<6} [{r.method}]{flag}  {r.record.message}")

    if a.report:
        out = Path(a.report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report.render(summary, results, a.log), encoding="utf-8")
        print(f"报告已写入 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
