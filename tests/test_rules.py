import pytest

from analyzer import parser, rules
from analyzer.parser import Record


def rec(msg="x", status="FAIL", station="ST01", tid="T1", ts="2026-11-13 09:00:00", **kw) -> Record:
    return Record(ts, tid, "t", "comm", station, status, msg, **kw)


@pytest.mark.parametrize("msg, expected", [
    ("I2C NACK from address 0x48", "COMMUNICATION"),
    ("UART CRC mismatch on frame 12", "COMMUNICATION"),
    ("Sensor response timeout after 500ms", "TIMEOUT"),
    ("WDT reset detected, boot count=3", "WATCHDOG_RESET"),
    ("VCC out of range", "VOLTAGE"),
    ("Assert failed: level=85, expected <70", "ASSERTION"),
    ("Fixture probe 3 not connected", "FIXTURE"),
])
def test_standard_messages(msg, expected):
    assert rules.match_message(msg)[0] == expected


@pytest.mark.parametrize("msg, expected", [  # v2 新增的同义写法
    ("Bus 2: slave did not acknowledge", "COMMUNICATION"),
    ("No ACK received from EEPROM", "COMMUNICATION"),
    ("Operation timed out waiting for sensor", "TIMEOUT"),
    ("Request timed-out after 3 retries", "TIMEOUT"),
    ("传感器响应超时", "TIMEOUT"),
    ("等待传感器应答超时", "TIMEOUT"),
    ("Watchdog triggered system reset", "WATCHDOG_RESET"),
    ("看门狗复位", "WATCHDOG_RESET"),
    ("Brown-out reset at power on", "VOLTAGE"),
    ("Brownout detected", "VOLTAGE"),
    ("Supply under-voltage detected", "VOLTAGE"),
    ("Pogo pin contact failure on test jig", "FIXTURE"),
])
def test_v2_synonyms(msg, expected):
    assert rules.match_message(msg)[0] == expected


def test_ambiguous_reboot_is_left_to_llm():
    # 意外重启可能是看门狗，也可能是掉电：故意不写规则，避免规则判错
    assert rules.match_message("Device rebooted unexpectedly during self-test") is None


def test_jig_must_be_a_whole_word():
    assert rules.match_message("jiggle detected") is None


def test_unknown_message_goes_to_llm():
    assert rules.match_message("Gas sensor baseline drifted") is None


def test_keyword_inside_other_word_does_not_match():
    # 「CRC」作为独立单词才算，避免误伤
    assert rules.match_message("SCRCX module ok?") is None


def test_voltage_out_of_range_by_measurement():
    r = rec("Read value", measured=2.9, lower_limit=3.135, upper_limit=3.465, unit="V")
    assert rules.classify(r) == ("VOLTAGE", "measured_out_of_range")


def test_voltage_in_range_is_not_flagged():
    r = rec("Read value", measured=3.3, lower_limit=3.135, upper_limit=3.465, unit="V")
    assert not rules.voltage_out_of_range(r)


def test_non_voltage_unit_is_ignored():
    r = rec("x", measured=85, upper_limit=70, unit="%")
    assert not rules.voltage_out_of_range(r)


def test_station_streak_marks_fixture():
    rs = [rec(tid=f"T{i}", ts=f"2026-11-13 09:0{i}:00", station="ST03") for i in range(4)]
    ids = rules.station_streaks(rs)
    assert ids == {"T0", "T1", "T2", "T3"}
    assert rules.classify(rs[0], ids) == ("FIXTURE", "station_streak")


def test_pass_breaks_streak():
    rs = [rec(tid="T1", station="ST01"), rec(tid="T2", station="ST01"),
          rec(tid="T3", station="ST01", status="PASS"), rec(tid="T4", station="ST01")]
    assert rules.station_streaks(rs) == set()


def test_streaks_are_per_station():
    rs = [rec(tid="T1", station="ST01"), rec(tid="T2", station="ST02"), rec(tid="T3", station="ST01")]
    assert rules.station_streaks(rs) == set()


def test_sample_log_fixture_station():
    records = parser.load("data/logs/sample.csv")
    assert rules.station_streaks(records) == {"T011", "T012", "T013", "T014"}
