-- 학생 포뮬러 전기차 A-FA 2026-08-11 실주행 로그용 스키마 (SQLite)
-- 원본 CSV 48열 중 값이 하나도 없는 메타 열 11개는 뺐다 (README 참고).

PRAGMA foreign_keys = ON;

-- 주행 1회 = 로그 파일 1개
CREATE TABLE session (
    session_id  INTEGER PRIMARY KEY,
    file_name   TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL,          -- 예: 오후1차
    log_date    TEXT NOT NULL,          -- YYYY-MM-DD
    row_count   INTEGER NOT NULL,
    format      TEXT NOT NULL DEFAULT 'v1_mcu',   -- rules/formats.csv 의 형식 (2026-11-21)
    has_clock   INTEGER NOT NULL DEFAULT 1        -- MCU 시각이 있으면 1. 0 이면 누락·시각·재시작 검사는 해당 없음(NULL)
);

-- 원본 한 행 = 샘플 하나 (MCU가 약 10 ms마다 보냄)
-- row_no 는 파일 안 순서. 시각이 깨진 행이 있어서 정렬 기준은 stm_ms 가 아니라 row_no 다.
CREATE TABLE sample (
    session_id            INTEGER NOT NULL REFERENCES session(session_id),
    row_no                INTEGER NOT NULL,
    ts_utc                TEXT,     -- 라즈베리파이가 받은 시각 (UTC)
    stm_ms                INTEGER,  -- MCU 시계 [ms]
    fr REAL, fl REAL, rr REAL, rl REAL,          -- 서스펜션 변위
    x_g REAL, y_g REAL, z_g REAL,                -- 가속도 [g]
    ecu_temp REAL,
    steering_angle REAL, steering_speed REAL,
    inv_temp_igt REAL, inv_temp_motor REAL,
    inv_motor_speed REAL,
    vehicle_speed_kmh REAL,
    inv_dc_current REAL,      -- 인버터 DC 전류 [A]
    inv_voltage REAL,         -- 인버터 DC 전압 [V]
    motor_precharge INTEGER, motor_main_contactor INTEGER, motor_inverter_mode INTEGER,
    inv_shudder_torque REAL,
    inv_id_feedback REAL, inv_iq_feedback REAL,
    inv_torque_commanded REAL, inv_torque_feedback REAL,
    inv_id_command REAL, inv_iq_command REAL,
    bms_charge REAL,
    bms_voltage REAL,         -- 배터리 팩 전압 [V]
    bms_current REAL,         -- 배터리 팩 전류 [A] (원본 그대로, 보정 전)
    bms_ccl REAL, bms_dcl REAL,
    bms_temp_maxvalue REAL,
    bms_capacity REAL,
    can1 INTEGER, can2 INTEGER,
    PRIMARY KEY (session_id, row_no)
);

-- 신호 정의서: 열 이름, 뜻, 단위, 들어오는 통신선
CREATE TABLE signal_def (
    column_name TEXT PRIMARY KEY,
    meaning     TEXT NOT NULL,
    unit        TEXT,
    bus         TEXT
);

-- 배율 보정은 쿼리 안에 숫자로 박지 않고 표로 관리한다
CREATE TABLE scale_correction (
    column_name TEXT PRIMARY KEY REFERENCES signal_def(column_name),
    factor      REAL NOT NULL,
    reason      TEXT NOT NULL,
    decided_on  TEXT NOT NULL
);

-- 어떤 파일을 언제 넣었는지. 같은 파일(내용 해시가 같음)은 다시 넣지 않는다.
CREATE TABLE ingest_log (
    sha256      TEXT PRIMARY KEY,
    file_name   TEXT NOT NULL,
    session_id  INTEGER NOT NULL REFERENCES session(session_id),
    loaded_at   TEXT NOT NULL
);

-- 품질 경고 규칙도 코드가 아니라 표로 둔다. 기준을 바꿀 때 코드를 안 고쳐도 된다.
CREATE TABLE quality_rule (
    metric      TEXT PRIMARY KEY,   -- 품질 지표 이름 (pipeline.py 가 계산)
    op          TEXT NOT NULL CHECK (op IN ('>', '<')),
    threshold   REAL NOT NULL,
    message     TEXT NOT NULL
);

-- 숫자로 못 읽은 칸 (빈칸은 NULL로 넣고 여기엔 안 남김)
CREATE TABLE load_issue (
    session_id  INTEGER NOT NULL REFERENCES session(session_id),
    row_no      INTEGER NOT NULL,
    column_name TEXT NOT NULL,
    raw_value   TEXT
);

CREATE INDEX idx_sample_load ON sample(session_id, inv_dc_current);

-- 모든 숫자 열의 튄 값 검사 기준 (rules/value_check.csv 에서 읽음, value_check.py 참고)
CREATE TABLE IF NOT EXISTS value_check (
    column_name   TEXT PRIMARY KEY,
    kind          TEXT NOT NULL,     -- 값 유지 / 매 행 바뀜 / 가속도
    range_p1_p99  REAL NOT NULL,     -- 분석용 3세션의 1%~99% 분위 폭
    multiple      REAL NOT NULL,     -- min_dev = range x multiple
    min_dev       REAL NOT NULL      -- |값 - 5행 중앙값| 이 이것보다 크면 튄 값
);

-- 튄 값 검사 결과. 뷰로 매번 계산하면 30열 x 20만 행이라 약 15초 → 적재할 때 한 번 계산해 둔다 (db.refresh_flags)
CREATE TABLE IF NOT EXISTS value_flag (
    session_id  INTEGER NOT NULL,
    row_no      INTEGER NOT NULL,
    column_name TEXT NOT NULL,
    value       REAL NOT NULL,
    median5     REAL NOT NULL,
    PRIMARY KEY (session_id, row_no, column_name)
);

-- 보정 계수를 적용한 전류. 보정 표가 비어 있으면 factor 1.0
CREATE VIEW sample_corrected AS
SELECT s.*,
       s.bms_current * COALESCE(
           (SELECT factor FROM scale_correction WHERE column_name = 'bms_current'), 1.0
       ) AS bms_current_corr
FROM sample s;
