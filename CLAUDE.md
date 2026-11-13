# 硬件测试日志分析工具 · 项目约定

## 目标
读取嵌入式设备的测试日志 CSV，自动筛出失败记录，判断失败原因，建议分派给对应团队；拿不准的标记人工审核。

## 原则
- 这是**固定流程的自动化工具，不是 Agent**：读取 → 清洗 → 规则分类 → LLM 兜底 → 报告。
- **规则优先**：能用规则判断的不交给 LLM；规则认不出的才调用一次 LLM。
- LLM 走 OpenAI 兼容接口，读环境变量 `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`；
  没有 key 时走 **mock 模式**，整个流程（含 CI）仍能运行。
- LLM 输出必须用 **Pydantic** 校验，失败重试一次；`confidence < 0.7` 标记 `needs_review`。
- 分派规则是**假设**，需要和领域专家确认，不让 AI 补全未知规则。

## 失败分类（固定 7 类）
| 分类 | 建议分派 |
| --- | --- |
| TIMEOUT / COMMUNICATION / WATCHDOG_RESET | 嵌入式软件 |
| VOLTAGE | 硬件 |
| FIXTURE | 测试工程师 |
| ASSERTION / UNKNOWN | 待人工确认 |

## 目录
- `src/analyzer/`：parser（清洗统计）、rules（规则）、schema（Pydantic）、llm（LLM 兜底）、pipeline（串联）、report（报告）、cli（入口）
- `tests/`：pytest，只测确定性代码，LLM 用假客户端
- `evals/`：评测集（dev / test 切分）与评测脚本
- `docs/ITERATION_LOG.md`：每次迭代的现象、原因、修改、结果

## 约定
- 调规则只看 dev 集，最终数字只报 test 集。
- 每次修改规则或提示词后：`pytest -q && python evals/run_eval.py`。
