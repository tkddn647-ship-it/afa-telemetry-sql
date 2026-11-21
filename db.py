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


FORMATS_CSV = ROOT / "rules" / "formats.csv"


def formats() -> dict[str, dict]:
    """rules/formats.csv -> {형식: {"detect": 머리줄에 있으면 이 형식인 열, "clock": 시계 열 또는 "", "map": {표준 열: 원본 열 또는 ""}}}.
    표에 없는 표준 열은 원본에서 같은 이름(대소문자 무시)을 찾는다. 원본 열이 "" 이면 그 형식엔 없는 신호 -> NULL."""
    out: dict[str, dict] = {}
    with open(FORMATS_CSV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            f = out.setdefault(r["format"], {"detect": None, "clock": None, "map": {}})
            if r["canonical"] == "_detect":
                f["detect"] = r["source"]
            elif r["canonical"] == "_clock":
                f["clock"] = r["source"]
            else:
                f["map"][r["canonical"].lower()] = r["source"]
    return out


def detect_format(header: list[str]) -> str:
    """머리줄로 형식을 고른다 (formats.csv 의 순서대로 처음 맞는 것). 모르는 형식이면 어떤 열이 있었는지 알려 주고 멈춘다."""
    have = {h.strip().lower() for h in header}
    for name, f in formats().items():
        if f["detect"] and f["detect"].lower() in have:
            return name
    raise ValueError(f"모르는 로그 형식: 머리줄 {header[:8]}... — rules/formats.csv 에 형식을 추가하세요")


def silent_columns(con: sqlite3.Connection) -> dict[str, list[str]]:
    """세션 -> 세션 내내 NULL 이거나 0 인 신호 (기록 안 됐거나 연결 안 된 신호). 7월 로그는 인버터·BMS 가 전부 0."""
    cols = [c.lower() for c in COLUMNS if c != "stm_ms"]
    expr = ", ".join(f"SUM({c} IS NOT NULL AND {c} != 0)" for c in cols)
    out = {}
    for row in con.execute(f"SELECT se.label, {expr} FROM sample s JOIN session se USING (session_id) GROUP BY se.session_id"):
        out[row[0]] = [c for c, n in zip(cols, row[1:]) if not n]
    return out


def migrate(con: sqlite3.Connection) -> None:
    """예전 DB의 session 표에 형식 열을 더한다 (2026-11-21). 예전 세션은 모두 v1_mcu."""
    have = {r[1] for r in con.execute("PRAGMA table_info(session)")}
    if "format" not in have:
        con.execute("ALTER TABLE session ADD COLUMN format TEXT NOT NULL DEFAULT 'v1_mcu'")
    if "has_clock" not in have:
        con.execute("ALTER TABLE session ADD COLUMN has_clock INTEGER NOT NULL DEFAULT 1")
    con.commit()


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
    migrate(con)
    table_cols = ["session_id", "row_no", "ts_utc"] + [c.lower() for c in COLUMNS]
    insert = f"INSERT INTO sample ({','.join(table_cols)}) VALUES ({','.join('?' * len(table_cols))})"
    opener = gzip.open if path.suffix == ".gz" else open
    rows, issues = [], []
    sid = (con.execute("SELECT COALESCE(MAX(session_id), 0) + 1 FROM session").fetchone()[0])
    with opener(path, "rt", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fmt = detect_format(reader.fieldnames or [])
        spec = formats()[fmt]
        lower = {h.strip().lower(): h for h in reader.fieldnames}
        src = {}                                               # 표준 열 -> 원본 머리줄 이름 (없으면 None)
        for col in COLUMNS:
            name = spec["map"].get(col.lower(), col)
            src[col] = lower.get(name.lower()) if name else None
        for row_no, rec in enumerate(reader, start=1):
            vals = [sid, row_no, rec.get("timestamp") or None]
            for col in COLUMNS:
                raw = rec.get(src[col], "") if src[col] else ""
                v, bad = _convert(col, raw or "")
                if bad:
                    issues.append((sid, row_no, col.lower(), raw))
                vals.append(v)
            rows.append(vals)
    m = re.search(r"(\d{4})(\d{2})(\d{2})", path.name)
    first_ts = rows[0][2] if rows else None
    if m:
        date = "-".join(m.groups())
    elif first_ts and re.match(r"\d{4}[/-]\d{2}[/-]\d{2}", first_ts):
        date = first_ts[:10].replace("/", "-")                 # 파일 이름에 날짜가 없으면 첫 행의 시각에서
    else:
        date = None
    label = label_of(path)
    if not re.search(r"sensor_log_\d{8}_", path.name) and first_ts:   # data.csv 처럼 이름으로 구분이 안 되는 파일
        label = f"{date}_{first_ts[11:19].replace(':', '')}" if date else label
    has_clock = 1 if spec["clock"] else 0
    stored_name = path.name if re.search(r"\d{8}", path.name) else f"{path.parent.name}/{path.name}"   # data.csv 가 여러 폴더에 있을 수 있음
    with con:
        con.execute("INSERT INTO session (session_id, file_name, label, log_date, row_count, format, has_clock) VALUES (?,?,?,?,?,?,?)",
                    (sid, stored_name, label, date, len(rows), fmt, has_clock))
        con.executemany(insert, rows)
        con.executemany("INSERT INTO load_issue VALUES (?,?,?,?)", issues)
        con.execute("INSERT INTO ingest_log VALUES (?,?,?,?)",
                    (digest, stored_name, sid, datetime.now().isoformat(timespec="seconds")))
    return sid, len(rows)
