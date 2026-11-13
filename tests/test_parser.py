import pytest

from analyzer import parser

HEADER = "timestamp,test_id,test_name,module,station,status,measured,lower_limit,upper_limit,unit,message\n"


def write(tmp_path, body: str):
    p = tmp_path / "log.csv"
    p.write_text(HEADER + body, encoding="utf-8")
    return p


def test_sample_log_loads():
    records = parser.load("data/logs/sample.csv")
    s = parser.summarize(records)
    assert s["total"] == 40
    assert s["failed"] == 16


def test_module_is_normalized(tmp_path):
    p = write(tmp_path,
              "2026-11-13 09:00:00,T1,a,COMM,ST01,FAIL,,,,,x\n"
              "2026-11-13 09:01:00,T2,a, Comm ,ST01,PASS,,,,,OK\n"
              "2026-11-13 09:02:00,T3,a,comm,ST01,FAIL,,,,,y\n")
    records = parser.load(p)
    assert {r.module for r in records} == {"comm"}
    assert parser.summarize(records)["fail_by_module"] == {"comm": 2}


def test_empty_module_becomes_unknown(tmp_path):
    p = write(tmp_path, "2026-11-13 09:00:00,T1,a,,ST01,FAIL,,,,,x\n")
    assert parser.load(p)[0].module == "unknown"


def test_bad_number_does_not_crash(tmp_path):
    p = write(tmp_path, "2026-11-13 09:00:00,T1,a,power,ST01,FAIL,abc,3.1,3.5,V,x\n")
    assert parser.load(p)[0].measured is None


def test_status_is_case_insensitive(tmp_path):
    p = write(tmp_path, "2026-11-13 09:00:00,T1,a,power,st01, fail ,,,,,x\n")
    r = parser.load(p)[0]
    assert r.failed and r.station == "ST01"


def test_header_only_file(tmp_path):
    p = write(tmp_path, "")
    records = parser.load(p)
    assert records == []
    assert parser.summarize(records)["total"] == 0


def test_missing_required_column(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("timestamp,test_id,status\n2026-11-13,T1,FAIL\n", encoding="utf-8")
    with pytest.raises(ValueError, match="缺少必要字段"):
        parser.load(p)


def test_records_sorted_by_time(tmp_path):
    p = write(tmp_path,
              "2026-11-13 09:05:00,T2,a,power,ST01,PASS,,,,,OK\n"
              "2026-11-13 09:00:00,T1,a,power,ST01,FAIL,,,,,x\n")
    assert [r.test_id for r in parser.load(p)] == ["T1", "T2"]
