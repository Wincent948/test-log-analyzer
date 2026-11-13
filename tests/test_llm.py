"""LLM 部分用假客户端测试：只测我们自己的代码（解析、校验、重试、阈值），不真的调用模型。"""
from types import SimpleNamespace

from analyzer import pipeline
from analyzer.llm import LLMClassifier
from analyzer.parser import Record


class FakeClient:
    """按顺序返回预设的回答；记录被调用了几次。"""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.calls += 1
        content = self.answers.pop(0)
        if isinstance(content, Exception):
            raise content
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def test_mock_mode_without_client(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    c = LLMClassifier()
    c.client = None
    out = c.classify("anything")
    assert out.mode == "mock" and out.category == "UNKNOWN" and out.needs_review


def test_valid_answer():
    fake = FakeClient('{"category": "COMMUNICATION", "reason": "设备没有应答", "confidence": 0.9}')
    out = LLMClassifier(client=fake, model="m").classify("Buzzer did not acknowledge")
    assert (out.category, out.mode, out.needs_review) == ("COMMUNICATION", "llm", False)


def test_extra_text_around_json_is_tolerated():
    fake = FakeClient('好的，结果如下：{"category": "TIMEOUT", "reason": "超时", "confidence": 0.8} 希望有帮助')
    assert LLMClassifier(client=fake, model="m").classify("x").category == "TIMEOUT"


def test_low_confidence_needs_review():
    fake = FakeClient('{"category": "VOLTAGE", "reason": "可能掉电", "confidence": 0.5}')
    out = LLMClassifier(client=fake, model="m").classify("x")
    assert out.category == "VOLTAGE" and out.needs_review


def test_invented_category_is_rejected_then_retried():
    fake = FakeClient('{"category": "NETWORK", "reason": "网络", "confidence": 0.9}',
                      '{"category": "COMMUNICATION", "reason": "通信", "confidence": 0.9}')
    out = LLMClassifier(client=fake, model="m").classify("x")
    assert fake.calls == 2 and out.category == "COMMUNICATION" and out.attempts == 2


def test_confidence_out_of_range_is_rejected():
    fake = FakeClient('{"category": "TIMEOUT", "reason": "超时", "confidence": 95}',
                      '{"category": "TIMEOUT", "reason": "超时", "confidence": 95}')
    out = LLMClassifier(client=fake, model="m").classify("x")
    assert out.mode == "fallback" and out.category == "UNKNOWN" and out.needs_review


def test_api_error_falls_back_without_retry():
    fake = FakeClient(ConnectionError("down"), '{"category": "TIMEOUT", "reason": "x", "confidence": 0.9}')
    out = LLMClassifier(client=fake, model="m").classify("x")
    assert fake.calls == 1 and out.mode == "fallback"


def test_rules_first_llm_only_for_unmatched():
    fake = FakeClient('{"category": "WATCHDOG_RESET", "reason": "自检中意外重启", "confidence": 0.75}')
    llm = LLMClassifier(client=fake, model="m")
    recs = [Record("2026-11-13 09:00:00", "T1", "t", "comm", "ST01", "FAIL", "I2C NACK from 0x48"),
            Record("2026-11-13 09:01:00", "T2", "t", "comm", "ST01", "PASS", "OK"),
            Record("2026-11-13 09:02:00", "T3", "t", "alarm", "ST01", "FAIL", "Device rebooted unexpectedly")]
    results = pipeline.analyze(recs, llm)
    assert fake.calls == 1                       # 只有规则认不出的那一条调用了 LLM
    assert [r.method for r in results] == ["rule", "llm"]
    assert results[1].owner == "嵌入式软件"


def test_assertion_always_needs_review():
    llm = LLMClassifier(client=FakeClient(), model="m")
    r = Record("2026-11-13 09:00:00", "T1", "t", "smoke", "ST01", "FAIL", "Assert failed: x")
    res = pipeline.analyze([r], llm)[0]
    assert res.category == "ASSERTION" and res.needs_review
