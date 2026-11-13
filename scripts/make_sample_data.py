"""生成模拟测试日志 data/logs/sample.csv（固定内容，可重复生成）。

设计要点：
- 覆盖 7 类失败；同一类既有标准写法，也有规则不容易认出的写法（交给 LLM）
- 故意放脏数据：module 大小写不一致、前后空格、module 为空
- ST03 测试台连续失败 4 次（模拟夹具故障）；其他测试台的失败之间都隔着 PASS
用法：python scripts/make_sample_data.py
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "logs" / "sample.csv"
FIELDS = ["timestamp", "test_id", "test_name", "module", "station", "status",
          "measured", "lower_limit", "upper_limit", "unit", "message"]

# (test_name, module, station, status, measured, lower, upper, unit, message)
ROWS = [
    ("VCC_Check", "power", "ST01", "PASS", 3.30, 3.135, 3.465, "V", "OK"),
    ("Smoke_Calib", "smoke_sensor", "ST02", "PASS", "", "", "", "", "OK"),
    ("I2C_Temp_Read", "comm", "ST01", "FAIL", "", "", "", "", "I2C NACK from address 0x48"),
    ("Gas_Baseline", "gas_sensor", "ST04", "PASS", 412, 350, 450, "ppm", "OK"),
    ("Alarm_Tone", "alarm", "ST01", "PASS", 85, 80, 95, "dB", "OK"),
    ("VCC_Check", "power", "ST02", "FAIL", 2.91, 3.135, 3.465, "V", "VCC out of range"),
    ("UART_Loopback", "comm", "ST04", "PASS", "", "", "", "", "OK"),
    ("Smoke_Response", "smoke_sensor", "ST01", "FAIL", "", "", "", "", "Sensor response timeout after 500ms"),
    ("Alarm_LED", "alarm", "ST02", "PASS", "", "", "", "", "OK"),
    ("Gas_Span", "gas_sensor", "ST01", "PASS", 1010, 950, 1050, "ppm", "OK"),
    # ST03 连续 4 次失败，症状各不相同 → 更可能是夹具问题
    ("Gas_Span", "gas_sensor", "ST03", "FAIL", "", "", "", "", "Probe 3 contact resistance high"),
    ("Alarm_Tone", "alarm", "ST03", "FAIL", "", "", "", "", "No response from DUT"),
    ("SPI_Flash_ID", "COMM", "ST03", "FAIL", "", "", "", "", "Measurement unstable, retry exceeded"),
    ("VCC_Check", "power", "ST03", "FAIL", 0.0, 3.135, 3.465, "V", "Read value 0.00V"),
    ("Smoke_Calib", "smoke_sensor", "ST02", "PASS", "", "", "", "", "OK"),
    ("UART_Loopback", "comm", "ST01", "PASS", "", "", "", "", "OK"),
    ("CAN_Heartbeat", " Comm ", "ST04", "PASS", "", "", "", "", "OK"),
    ("Boot_Selftest", "alarm", "ST02", "FAIL", "", "", "", "", "WDT reset detected, boot count=3"),
    ("VCC_Check", "power", "ST04", "PASS", 3.28, 3.135, 3.465, "V", "OK"),
    ("Gas_Baseline", "gas_sensor", "ST02", "PASS", 398, 350, 450, "ppm", "OK"),
    ("Smoke_Threshold", "smoke_sensor", "ST04", "FAIL", 85, "", 70, "%", "Assert failed: smoke_level=85, expected <70"),
    ("Alarm_LED", "alarm", "ST01", "PASS", "", "", "", "", "OK"),
    ("UART_Frame", "comm", "ST02", "FAIL", "", "", "", "", "UART CRC mismatch on frame 12"),
    ("VCC_Check", "power", "ST01", "PASS", 3.31, 3.135, 3.465, "V", "OK"),
    ("Gas_Drift", "gas_sensor", "ST01", "FAIL", "", "", "", "", "Gas sensor baseline drifted beyond calibration window"),
    ("Smoke_Calib", "smoke_sensor", "ST04", "PASS", "", "", "", "", "OK"),
    ("Boot_Selftest", "", "ST04", "FAIL", "", "", "", "", "Device rebooted unexpectedly during self-test"),
    ("Alarm_Tone", "alarm", "ST02", "PASS", 88, 80, 95, "dB", "OK"),
    ("Gas_Span", "gas_sensor", "ST01", "PASS", 990, 950, 1050, "ppm", "OK"),
    ("Buzzer_Driver", "alarm", "ST01", "FAIL", "", "", "", "", "Buzzer driver did not acknowledge on bus 1"),
    ("UART_Loopback", "comm", "ST04", "PASS", "", "", "", "", "OK"),
    ("VCC_Check", "power", "ST02", "PASS", 3.29, 3.135, 3.465, "V", "OK"),
    ("Power_On", "power", "ST04", "FAIL", "", "", "", "", "Brown-out detected at startup"),
    ("Smoke_Response", "smoke_sensor", "ST01", "PASS", "", "", "", "", "OK"),
    ("Alarm_LED", "alarm", "ST04", "PASS", "", "", "", "", "OK"),
    ("Temp_Read", "comm", "ST02", "FAIL", "", "", "", "", "等待传感器应答超时"),
    ("Gas_Baseline", "gas_sensor", "ST01", "PASS", 405, 350, 450, "ppm", "OK"),
    ("Smoke_Calib", "smoke_sensor", "ST02", "PASS", "", "", "", "", "OK"),
    ("LED_Pattern", "smoke_sensor", "ST04", "FAIL", "", "", "", "", "Expected 3 LED blinks, observed 1"),
    ("VCC_Check", "power", "ST01", "PASS", 3.30, 3.135, 3.465, "V", "OK"),
]


def main() -> None:
    t0 = datetime(2026, 11, 13, 9, 0, 0)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(FIELDS)
        for i, r in enumerate(ROWS, start=1):
            ts = (t0 + timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M:%S")
            w.writerow([ts, f"T{i:03d}", *r])
    print(f"写入 {OUT}（{len(ROWS)} 行）")


if __name__ == "__main__":
    main()
