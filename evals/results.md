# 评测结果

- 模式：mock（未调用 LLM）
- 题数：30

| 集合 | 题数 | 准确率 | 规则覆盖率 | 规则精确率 | LLM 准确率 | mock 未判 | 需人工确认 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| dev | 20 | 85% | 80% | 100% | — | 4 | 5 |
| test | 10 | 90% | 90% | 100% | — | 1 | 2 |

## 判错 / 未判出（4 条）

| id | 集合 | 日志 | 期望 | 实际 | 判断方式 |
| --- | --- | --- | --- | --- | --- |
| D17 | dev | Expected 3 LED blinks, observed 1 | 断言失败 | 无法判断 | mock |
| D18 | dev | Gas baseline drifted beyond calibration window | 断言失败 | 无法判断 | mock |
| D19 | dev | Device rebooted unexpectedly during self-test | 看门狗复位 | 无法判断 | mock |
| X10 | test | Self-test result mismatch on alarm relay | 断言失败 | 无法判断 | mock |
