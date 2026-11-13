"""LLM 兜底分类：只处理规则认不出的记录，每条只问一次（失败重试一次）。

- OpenAI 兼容接口，读 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL
- 没有 LLM_API_KEY → mock 模式：不调用模型，返回 UNKNOWN，交给人工
- 输出用 Pydantic 校验；两次都不合格 → UNKNOWN + 人工审核
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from analyzer.schema import Classification

REVIEW_THRESHOLD = 0.7

SYSTEM_PROMPT = """你是嵌入式设备产线测试的失败分类助手。根据一条失败测试的日志，判断失败原因属于以下哪一类：
- TIMEOUT：等待响应超时
- COMMUNICATION：芯片或设备之间通信出错（无应答、校验错误、总线错误）
- WATCHDOG_RESET：程序卡死被看门狗复位，或设备意外重启
- VOLTAGE：供电电压异常（过压、欠压、掉电）
- FIXTURE：测试设备本身的问题（探针、夹具、线缆、仪器），不是产品的问题
- ASSERTION：测量值或行为与期望不符，但看不出具体原因
- UNKNOWN：信息不足，无法判断
规则：
1. 只根据日志内容判断，不要猜测日志里没有的信息；拿不准就降低 confidence 或选 UNKNOWN。
2. 只输出一个 JSON 对象，不要输出其他文字：{"category": "...", "reason": "一句话理由", "confidence": 0到1的小数}"""


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


@dataclass
class LLMResult:
    category: str
    reason: str
    confidence: float
    needs_review: bool
    mode: str                      # llm / mock / fallback
    attempts: int = 0
    errors: list[str] = field(default_factory=list)


def parse_json(text: str) -> dict:
    """模型偶尔会在 JSON 外面多说话，只取第一段 {...}。"""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        raise ValueError("没有找到 JSON")
    return json.loads(m.group(0))


class LLMClassifier:
    def __init__(self, client=None, model: str | None = None):
        _load_dotenv()
        self.model = model or os.getenv("LLM_MODEL", "")
        self.client = client
        if self.client is None and os.getenv("LLM_API_KEY"):
            from openai import OpenAI
            self.client = OpenAI(base_url=os.getenv("LLM_BASE_URL") or None,
                                 api_key=os.getenv("LLM_API_KEY"), timeout=30, max_retries=1)

    @property
    def offline(self) -> bool:
        return self.client is None

    def classify(self, message: str, context: str = "") -> LLMResult:
        if self.offline:
            return LLMResult("UNKNOWN", "mock 模式：未配置 LLM，交给人工判断", 0.0, True, "mock")
        user = f"日志：{message}\n上下文：{context or '无'}"
        errors: list[str] = []
        for attempt in (1, 2):  # 格式不对就重试一次
            try:
                resp = self.client.chat.completions.create(
                    model=self.model, temperature=0, max_tokens=200,
                    extra_body={"enable_thinking": False},   # 关掉千问的「先思考」
                    messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}])
                out = Classification.model_validate(parse_json(resp.choices[0].message.content))
                review = out.confidence < REVIEW_THRESHOLD or out.category == "UNKNOWN"
                return LLMResult(out.category, out.reason, out.confidence, review, "llm", attempt, errors)
            except (ValidationError, ValueError, json.JSONDecodeError) as e:
                errors.append(f"第 {attempt} 次输出不合格：{type(e).__name__}")
            except Exception as e:  # noqa: BLE001 网络、鉴权等问题：不再重试，直接交给人工
                errors.append(f"调用失败：{type(e).__name__}")
                break
        return LLMResult("UNKNOWN", "LLM 输出两次都不合格或调用失败，交给人工", 0.0, True, "fallback",
                         len(errors), errors)
