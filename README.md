# 硬件测试日志分析工具

自动分析嵌入式设备的产线测试日志：筛出失败记录、判断失败原因、建议分派给对应团队；拿不准的交给人确认。

## 解决什么问题
测试台每天产出大量日志。人工逐条看「这条失败是软件问题、硬件问题，还是测试设备坏了」又慢又容易派错人：
夹具接触不良却发给软件工程师，对方查半天代码才发现产品没问题。
这个工具把**测试工程师判断失败原因的经验**写成规则，规则覆盖不了的写法再交给 LLM，并保留人工审核。

## 架构
```
测试日志 CSV
   ↓ parser.py    读取、清洗（模块名统一大小写、空值标 unknown）、统计      ← 确定性代码
   ↓ rules.py     ① 同一测试台连续失败 ≥3 次 → 夹具故障                       ← 确定性代码
   ↓              ② 电压测量值超出上下限 → 电压异常
   ↓              ③ 日志关键词（NACK、timeout、WDT、brown-out …）
   ↓ llm.py       规则认不出的才调用一次 LLM；Pydantic 校验输出，失败重试一次    ← LLM
   ↓              置信度 < 0.7、断言失败、无法判断 → 标记人工确认              ← 人工审核点
   ↓ report.py    Markdown 报告：分派建议、失败明细、需人工确认清单
```

## AI 与确定性代码的分工
| 环节 | 用什么 | 为什么 |
| --- | --- | --- |
| 读取、清洗、统计 | 代码 | 结果必须稳定、可复现 |
| 标准写法的失败（NACK、timeout、WDT…） | 规则 | 快、免费、不会胡说；规则精确率要求 100% |
| 夹具故障（同一测试台连续失败） | 规则 | 需要看多条记录的时间顺序，LLM 单条看不出来 |
| 写法五花八门、需要理解语义的日志 | LLM | 规则写不完；例如「意外重启」可能是看门狗也可能是掉电 |
| 断言失败、低置信度、无法判断 | 人工 | 分不清该找谁，或 AI 没把握 |

**为什么不用 Agent**：每条日志要做的事完全相同，流程固定，没有「事先不知道要查几次」的情况。
用 Agent 只会更慢、更贵、更难测试。LLM 在这里只是流程中的一个分类步骤。

## Quick Start
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 不配 key 也能跑（mock 模式：规则认不出的标记人工确认）
python -m analyzer.cli data/logs/sample.csv --report reports/report.md

# 接入 LLM：复制 .env.example 为 .env，填写 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL
cp .env.example .env
python -m analyzer.cli data/logs/sample.csv --report reports/report.md
```
日志格式见 `data/logs/sample.csv`；必需字段：`timestamp, test_id, test_name, module, station, status, message`，
可选字段：`measured, lower_limit, upper_limit, unit`。示例数据由 `scripts/make_sample_data.py` 生成。

## 测试方法
| 层次 | 命令 | 测什么 |
| --- | --- | --- |
| 单元测试（47 个） | `pytest -q` | 清洗、规则、Pydantic 校验、重试、阈值；LLM 用假客户端，不花钱 |
| 评测（30 条） | `python evals/run_eval.py` | 分类准不准：准确率、规则覆盖率、规则精确率、LLM 准确率 |
| CI | GitHub Actions | 每次 push 自动跑单元测试 + 评测；**规则判错一条就失败** |

评测集分 **dev（20 条，用来调规则）** 和 **test（10 条，只用来报告结果）**，防止对着同一批题反复调参。

当前结果（mock 模式，只评规则部分）：

| 集合 | 准确率 | 规则覆盖率 | 规则精确率 |
| --- | --- | --- | --- |
| dev | 85% | 80% | 100% |
| test | 90% | 90% | 100% |

迭代过程（规则 v1 → v2，test 集 50% → 90%）见 [docs/ITERATION_LOG.md](docs/ITERATION_LOG.md)。

## 已知限制
- 示例日志和评测集是**模拟数据**，题目和规则出自同一人，test 集可能偏向规则能覆盖的写法。
- 分类标准答案和分派表（`taxonomy.py`）是**初步假设**，需要与测试、硬件、嵌入式团队确认。
- 夹具规则只看「连续失败次数」，没有区分是不是同一台产品反复测试。
- LLM 部分尚未用真实模型完成评测（需要配置 API key，见迭代记录「迭代 2」）。

## 后续改进
- 用真实产线日志扩充评测集，由测试工程师标注标准答案。
- 接入真实 LLM 评测，按失败案例调整提示词。
- 报告按测试台、固件版本做趋势统计（例如新固件上线后通信错误是否变多）。
- 封装成 MCP 工具或 Skill，让团队在 Claude Code 等工具里直接调用。

## FAQ
**没有 API key 能用吗？** 能。规则部分照常工作，规则认不出的标记为「需人工确认」。CI 也是这样跑的。

**为什么夹具规则优先级最高？** 不同产品在同一台测试设备上接连失败、症状还各不相同，更可能是设备本身的问题。
这时如果按日志文字去分派，会把问题发给错误的团队。

**怎么新增一种失败写法？** 在 `rules.py` 的 `PATTERNS` 里补充关键词 → 在 `tests/test_rules.py` 加用例 →
`pytest -q && python evals/run_eval.py --split dev`。确认规则精确率仍是 100% 再提交。

**LLM 输出格式不对怎么办？** Pydantic 校验失败会重试一次；还不行就判为「无法判断」并交给人工，不会让错误结果流到报告里。
