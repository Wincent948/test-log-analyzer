"""生成 Markdown 报告。"""
from __future__ import annotations

from collections import Counter

from analyzer.pipeline import Result
from analyzer.taxonomy import LABEL_ZH


def _esc(s: str) -> str:
    return (s or "").replace("|", "\\|")


def render(summary: dict, results: list[Result], source: str) -> str:
    by_cat = Counter(r.category for r in results)
    by_owner = Counter(r.owner for r in results)
    by_method = Counter(r.method for r in results)
    review = [r for r in results if r.needs_review]
    L = [
        "# 测试日志分析报告",
        "",
        f"- 日志文件：`{source}`",
        f"- 总测试 **{summary['total']}** 条，失败 **{summary['failed']}** 条，通过率 {summary['pass_rate']:.1%}",
        f"- 失败最多的模块：{', '.join(f'{k}（{v}）' for k, v in summary['fail_by_module'].items()) or '无'}",
        f"- 失败最多的测试台：{', '.join(f'{k}（{v}）' for k, v in summary['fail_by_station'].items()) or '无'}",
        f"- 判断方式：{', '.join(f'{k} {v} 条' for k, v in by_method.items()) or '无'}；需人工确认 **{len(review)}** 条",
        "",
        "## 分派建议",
        "",
        "| 建议找谁 | 条数 |",
        "| --- | --- |",
        *[f"| {k} | {v} |" for k, v in by_owner.most_common()],
        "",
        "## 失败分类",
        "",
        "| 分类 | 条数 |",
        "| --- | --- |",
        *[f"| {LABEL_ZH[k]}（{k}） | {v} |" for k, v in by_cat.most_common()],
        "",
        "## 失败明细",
        "",
        "| 测试 | 模块 | 测试台 | 日志 | 分类 | 建议找谁 | 判断方式 | 置信度 | 需人工确认 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in results:
        L.append(f"| {r.record.test_id} | {r.record.module} | {r.record.station} | {_esc(r.record.message)} | "
                 f"{LABEL_ZH[r.category]} | {r.owner} | {r.method}：{_esc(r.detail)} | {r.confidence:.2f} | "
                 f"{'⚠️ 是' if r.needs_review else '否'} |")
    L += ["", "## 需人工确认", ""]
    L += [f"- **{r.record.test_id}**「{r.record.message}」→ {LABEL_ZH[r.category]}（{r.method}）" for r in review] or ["- 无"]
    L += ["", "> 分派规则为初步假设，需与领域专家确认。", ""]
    return "\n".join(L)
