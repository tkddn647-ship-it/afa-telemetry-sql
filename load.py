"""CSV.gz 로그를 SQLite로 넣는다.

사용: python load.py data/*.csv.gz            -> telemetry.db 생성
빈칸은 NULL, 숫자로 못 읽은 칸은 NULL로 넣고 load_issue 표에 원본 글자를 남긴다.
"""
from __future__ import annotations

import csv
import gzip
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DB = ROOT / "telemetry.db"

# 원본 CSV 열 -> 표 열 (대소문자만 다른 것은 소문자로 통일)
COLUMNS = [
    "stm_ms", "FR", "FL", "RR", "RL", "x_g", "y_g", "z_g", "ecu_temp",
    "steering_angle", "steering_speed", "inv_temp_igt", "inv_temp_motor",
    "inv_motor_speed", "vehicle_speed_kmh", "inv_dc_current", "inv_voltage",
    "motor_precharge", "motor_main_contactor", "motor_inverter_mode",
    "INV_shudder_torque", "INV_id_feedback", "INV_iq_feedback",
    "INV_torque_commanded", "INV_torque_feedback", "INV_id_command", "INV_iq_command",
    "bms_charge", "bms_voltage", "bms_current", "bms_ccl", "bms_dcl",
    "bms_temp_maxvalue", "bms_capacity", "can1", "can2",
]
INT_COLUMNS = {"stm_ms", "motor_precharge", "motor_main_contactor", "motor_inverter_mode", "can1", "can2"}

SIGNALS = [
    ("inv_dc_current", "인버터 DC 전류", "A", "CAN1 250 kbps (인버터)"),
    ("inv_voltage", "인버터 DC 전압", "V", "CAN1 250 kbps (인버터)"),
    ("bms_current", "배터리 팩 전류", "A", "CAN1 250 kbps (BMS)"),
    ("bms_voltage", "배터리 팩 전압", "V", "CAN1 250 kbps (BMS)"),
    ("steering_angle", "조향각", None, "CAN2 500 kbps (조향각 센서)"),
    ("vehicle_speed_kmh", "차량 속도", "km/h", None),
    ("stm_ms", "MCU 시계", "ms", None),
]
CORRECTIONS = [
    ("bms_current", 1.25,
     "부하 구간 bms_current/inv_dc_current 비율이 세션 3개 모두 약 0.80으로 일정 -> 스케일 계수 누락",
     "2026-08"),
]


def label_of(path: Path) -> str:
    m = re.search(r"sensor_log_\d{8}_(.+?)\.csv", path.name)
    return m.group(1) if m else path.stem


def convert(col: str, raw: str):
    if raw == "":
        return None, False
    try:
        v = float(raw)
    except ValueError:
        return None, True
    if col in INT_COLUMNS and v.is_integer():
        return int(v), False
    return v, False


def main(paths: list[str]) -> None:
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    con.executescript((ROOT / "sql" / "00_schema.sql").read_text(encoding="utf-8"))
    con.executemany("INSERT INTO signal_def VALUES (?,?,?,?)", SIGNALS)
    con.executemany("INSERT INTO scale_correction VALUES (?,?,?,?)", CORRECTIONS)

    table_cols = ["session_id", "row_no", "ts_utc"] + [c.lower() for c in COLUMNS]
    insert = f"INSERT INTO sample ({','.join(table_cols)}) VALUES ({','.join('?' * len(table_cols))})"

    for sid, p in enumerate(sorted(Path(x) for x in paths), start=1):
        with gzip.open(p, "rt", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            rows, issues = [], []
            for row_no, rec in enumerate(reader, start=1):
                vals = [sid, row_no, rec["timestamp"] or None]
                for col in COLUMNS:
                    v, bad = convert(col, rec.get(col, ""))
                    if bad:
                        issues.append((sid, row_no, col.lower(), rec[col]))
                    vals.append(v)
                rows.append(vals)
        date = re.search(r"(\d{4})(\d{2})(\d{2})", p.name).groups()
        con.execute("INSERT INTO session VALUES (?,?,?,?,?)",
                    (sid, p.name, label_of(p), "-".join(date), len(rows)))
        con.executemany(insert, rows)
        con.executemany("INSERT INTO load_issue VALUES (?,?,?,?)", issues)
        print(f"{p.name}: {len(rows)}행, 숫자로 못 읽은 칸 {len(issues)}개")

    con.commit()
    total = con.execute("SELECT COUNT(*) FROM sample").fetchone()[0]
    print(f"합계 {total}행 -> {DB.name}")
    con.close()


if __name__ == "__main__":
    main(sys.argv[1:] or [str(p) for p in (ROOT / "data").glob("*.csv.gz")])
