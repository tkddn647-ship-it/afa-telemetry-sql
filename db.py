"""DB 연결과 로그 적재. load.py, pipeline.py, ask.py, mcp_server.py 가 같이 쓴다."""
from __future__ import annotations

import csv
import gzip
import os
import hashlib
import re
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
DB = Path(os.environ.get("TELEMETRY_DB", ROOT / "telemetry.db"))   # CI는 가짜 데이터용 DB를 따로 씀

# 원본 CSV 열 (표에서는 소문자). 값이 하나도 없는 메타 열 11개는 넣지 않는다.
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
    ("bms_current", "배터리 팩 전류 (원본, 보정 전)", "A", "CAN1 250 kbps (BMS)"),
    ("bms_voltage", "배터리 팩 전압", "V", "CAN1 250 kbps (BMS)"),
    ("steering_angle", "조향각", None, "CAN2 500 kbps (조향각 센서)"),
    ("vehicle_speed_kmh", "차량 속도", "km/h", None),
    ("stm_ms", "MCU 시계 (깨진 값이 있어 정렬은 row_no로)", "ms", None),
]
CORRECTIONS = [
    ("bms_current", 1.25,
     "부하 구간 bms_current/inv_dc_current 비율이 세션 3개 모두 약 0.80으로 일정 -> 스케일 계수 누락",
     "2026-08"),
]
RULES = [
    ("누락률_pct", ">", 8.0, "샘플 누락이 8%를 넘음: 전송 방식이나 버퍼 확인"),
    ("깨진_비율_pct", ">", 0.05, "깨진 행이 0.05%를 넘음: 시리얼 배선·잡음 확인"),
    ("MCU_재시작", ">", 0, "주행 중 MCU가 재시작함: 전원·워치독 기록 확인"),
    ("위반_보정후_pct", ">", 30.0, "보정 뒤에도 인버터 전류가 팩 전류보다 큰 행이 30%를 넘음: 계수 재검토"),
]


def connect(path: Path = DB) -> sqlite3.Connection:
    return sqlite3.connect(path)


def connect_readonly(path: Path = DB) -> sqlite3.Connection:
    """AI가 짠 쿼리용. 파일을 읽기 전용으로 열고, 쓰기 문장은 DB 단에서도 막는다."""
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.execute("PRAGMA query_only = ON")
    return con


def create(path: Path = DB) -> sqlite3.Connection:
    if path.exists():
        path.unlink()
    con = connect(path)
    con.executescript((ROOT / "sql" / "00_schema.sql").read_text(encoding="utf-8"))
    con.executemany("INSERT INTO signal_def VALUES (?,?,?,?)", SIGNALS)
    con.executemany("INSERT INTO scale_correction VALUES (?,?,?,?)", CORRECTIONS)
    con.executemany("INSERT INTO quality_rule VALUES (?,?,?,?)", RULES)
    con.commit()
    return con


VALUE_CHECK_CSV = ROOT / "rules" / "value_check.csv"
SCHEMA_V2 = """
DROP TABLE IF EXISTS value_check;   -- 매번 CSV에서 다시 채우므로 열이 바뀌어도 안전하게 새로 만든다
CREATE TABLE value_check (column_name TEXT PRIMARY KEY, kind TEXT NOT NULL, range_p1_p99 REAL NOT NULL,
                          multiple REAL NOT NULL, min_dev REAL NOT NULL, digit_min_dev REAL);
CREATE TABLE IF NOT EXISTS value_flag (session_id INTEGER NOT NULL, row_no INTEGER NOT NULL, column_name TEXT NOT NULL,
                                       value REAL NOT NULL, median5 REAL NOT NULL, PRIMARY KEY (session_id, row_no, column_name));
"""


def refresh_flags(con: sqlite3.Connection, session_ids: list[int] | None = None) -> None:
    """깨진 값 표시를 최신으로: value_check 표를 CSV에서 다시 읽고, value_flag 를 다시 계산하고, 01_flags 뷰를 다시 만든다.
    session_ids 를 주면 그 세션만 다시 계산 (pipeline.py 가 새 로그만 처리할 때). 예전 DB에 표가 없으면 만든다."""
    con.executescript(SCHEMA_V2)
    with open(VALUE_CHECK_CSV, encoding="utf-8") as fh:
        rows = [(r["column_name"], r["kind"], float(r["range_p1_p99"]), float(r["multiple"]), float(r["min_dev"]),
                 float(r["digit_min_dev"]) if r.get("digit_min_dev") else None)
                for r in csv.DictReader(fh)]
    con.executemany("INSERT INTO value_check VALUES (?,?,?,?,?,?)", rows)
    ids = session_ids if session_ids is not None else [r[0] for r in con.execute("SELECT session_id FROM session")]
    con.execute("CREATE TEMP TABLE IF NOT EXISTS refresh_session (session_id INTEGER PRIMARY KEY)")
    con.execute("DELETE FROM temp.refresh_session")
    con.executemany("INSERT INTO temp.refresh_session VALUES (?)", [(i,) for i in ids])
    con.execute("DELETE FROM value_flag WHERE session_id IN (SELECT session_id FROM temp.refresh_session)")
    template = (ROOT / "sql" / "01a_value_flags.sql").read_text(encoding="utf-8")
    for (col,) in con.execute("SELECT column_name FROM value_check ORDER BY column_name").fetchall():
        con.execute(template.replace("{col}", col))
    con.commit()
    con.executescript((ROOT / "sql" / "01_flags.sql").read_text(encoding="utf-8"))


def label_of(path: Path) -> str:
    m = re.search(r"sensor_log_\d{8}_(.+?)\.csv", path.name)
    return m.group(1) if m else path.stem


def _convert(col: str, raw: str):
    if raw == "":
        return None, False
    try:
        v = float(raw)
    except ValueError:
        return None, True
    if col in INT_COLUMNS and v.is_integer():
        return int(v), False
    return v, False


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_file(con: sqlite3.Connection, path: Path) -> tuple[int | None, int]:
    """파일 하나를 넣는다. 이미 넣은 파일이면 (None, 0)."""
    digest = sha256_of(path)
    if con.execute("SELECT 1 FROM ingest_log WHERE sha256 = ?", (digest,)).fetchone():
        return None, 0
    table_cols = ["session_id", "row_no", "ts_utc"] + [c.lower() for c in COLUMNS]
    insert = f"INSERT INTO sample ({','.join(table_cols)}) VALUES ({','.join('?' * len(table_cols))})"
    opener = gzip.open if path.suffix == ".gz" else open
    rows, issues = [], []
    sid = (con.execute("SELECT COALESCE(MAX(session_id), 0) + 1 FROM session").fetchone()[0])
    with opener(path, "rt", encoding="utf-8", newline="") as fh:
        for row_no, rec in enumerate(csv.DictReader(fh), start=1):
            vals = [sid, row_no, rec.get("timestamp") or None]
            for col in COLUMNS:
                v, bad = _convert(col, rec.get(col, "") or "")
                if bad:
                    issues.append((sid, row_no, col.lower(), rec[col]))
                vals.append(v)
            rows.append(vals)
    m = re.search(r"(\d{4})(\d{2})(\d{2})", path.name)
    date = "-".join(m.groups()) if m else None
    with con:
        con.execute("INSERT INTO session VALUES (?,?,?,?,?)", (sid, path.name, label_of(path), date, len(rows)))
        con.executemany(insert, rows)
        con.executemany("INSERT INTO load_issue VALUES (?,?,?,?)", issues)
        con.execute("INSERT INTO ingest_log VALUES (?,?,?,?)",
                    (digest, path.name, sid, datetime.now().isoformat(timespec="seconds")))
    return sid, len(rows)
