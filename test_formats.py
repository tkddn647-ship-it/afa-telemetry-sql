"""로그 형식 대응 시험 (rules/formats.csv, 2026-11-21). 실제 로그 없이 돈다 (CI 용).

사용: python test_formats.py
가짜 로그(synth.py, 8월 형식 v1_mcu)를 7월 UDP 로거 형식(v0_udp: 열 이름이 다르고 MCU 시각 없음)으로 바꿔 쓴 뒤
둘 다 실제 적재 경로(파일 -> DB -> 값 검사 -> sql/)로 넣어 확인한다.
  1. 머리줄로 형식을 알아봄
  2. 대응한 신호는 행마다 값이 같고, 그 형식에 없는 신호는 NULL (0 이 아님)
  3. MCU 시각이 없는 형식은 누락·시각·재시작 지표가 None (해당 없음), v1 은 숫자
  4. 기록 안 된 신호가 필요한 지표는 None (예: 인버터 전류가 전부 0 이면 전류 불일치는 해당 없음)
  5. 값 검사: v0 세션의 SQL 표시 = pandas 구현(시각 없이 행 수로 판단, 같은 형식 기준)
  7. 형식 전용 기준: rules/value_check_<형식>.csv 가 있으면 그 형식 세션만 그 기준으로 판정 (없으면 기본).
     시험에선 v0 의 fl 기준을 1000 으로 바꾼 임시 기준을 끼워, 심은 튐이 v0 에서만 안 잡히는지 본다
  6. 모르는 형식은 머리줄을 알려 주며 멈춤
"""
from __future__ import annotations

import csv
import gzip
import random
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

import db
import pipeline
import synth
import verify

FAIL = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("통과 " if ok else "실패 ") + name + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def to_v0(df: pd.DataFrame) -> pd.DataFrame:
    """v1 표(머리줄 synth.HEADER)를 v0_udp 머리줄로. 대응은 rules/formats.csv 를 거꾸로 읽어서."""
    spec = db.formats()["v0_udp"]["map"]
    out = pd.DataFrame({"timestamp": df["timestamp"]})
    t0 = 1_048_195_805_281_169
    out["monotonic_ns"] = t0 + np.arange(len(df)) * 50_000            # 묶음으로 찍힌 수신 시각 흉내 (뜻 없음)
    for col in db.COLUMNS:
        src = spec.get(col.lower(), col)
        if not src:
            continue                                                  # v0 에 없는 신호
        v1_name = next(h for h in df.columns if h.lower() == col.lower())
        out[src] = df[v1_name]
    out["wheel_rpm"] = 0.0                                            # v0 에만 있는 열 (적재에서 버려져야 함)
    return out


def main() -> None:
    rng = random.Random(3)
    v1 = synth.session(6000, rng, 100_000)
    v1["inv_dc_current"] = 0.0                                        # 7월처럼 인버터 전류가 전부 0 인 경우
    v1.loc[2000, "FL"] = v1.loc[2000, "FL"] + 80                       # 튄 값 하나 (두 형식 모두 잡혀야 함)
    v0 = to_v0(v1)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p1 = td / "sensor_log_20990101_형식v1.csv.gz"
        p0 = td / "sensor_log_20990101_형식v0.csv.gz"
        for df, p in ((v1, p1), (v0, p0)):
            with gzip.open(p, "wt", encoding="utf-8", newline="") as fh:
                df.to_csv(fh, index=False)
        bad = td / "sensor_log_20990101_모름.csv"
        bad.write_text("a,b,c\n1,2,3\n", encoding="utf-8")

        con = db.create(td / "t.db")
        sid1, _ = db.load_file(con, p1)
        sid0, _ = db.load_file(con, p0)
        fmts = dict(con.execute("SELECT label, format FROM session").fetchall())
        check("1. 형식 알아보기", fmts == {"형식v1": "v1_mcu", "형식v0": "v0_udp"}, str(fmts))

        cols = [c.lower() for c in db.COLUMNS if c != "stm_ms"]
        a = pd.read_sql_query(f"SELECT {','.join(cols)} FROM sample WHERE session_id = {sid1} ORDER BY row_no", con)
        b = pd.read_sql_query(f"SELECT {','.join(cols)} FROM sample WHERE session_id = {sid0} ORDER BY row_no", con)
        absent = [c.lower() for c, s in db.formats()["v0_udp"]["map"].items() if not s and c != "stm_ms"]
        mapped = [c for c in cols if c not in absent]
        same = all(np.allclose(a[c].astype(float), b[c].astype(float), equal_nan=True) for c in mapped)
        nulls = all(b[c].isna().all() for c in absent)
        stm0 = con.execute(f"SELECT COUNT(stm_ms) FROM sample WHERE session_id = {sid0}").fetchone()[0]
        check("2. 대응한 신호는 값이 같고, 없는 신호는 NULL", same and nulls and stm0 == 0,
              f"대응 {len(mapped)}열 같음={same}, 없는 {len(absent)}열 NULL={nulls}, v0 stm_ms 값 {stm0}개")

        m = pipeline.session_metrics(con)
        clock = ["누락률_pct", "빠진_샘플", "MCU_재시작", "시각_깨짐", "결합비", "그밖_누락"]
        check("3. 시각 없는 형식은 누락·시각 지표 해당 없음",
              all(m["형식v0"].get(k) is None for k in clock) and all(m["형식v1"].get(k) is not None for k in clock[:4]),
              f"v0 {[m['형식v0'].get(k) for k in clock]}, v1 누락률 {m['형식v1'].get('누락률_pct')}")
        silent = db.silent_columns(con)
        need = ["전류_불일치", "열림중_전류_행"]
        check("4. 기록 안 된 신호가 필요한 지표는 해당 없음",
              "inv_dc_current" in silent["형식v1"] and all(m[l].get(k) is None for l in m for k in need),
              f"v1 기록 안 됨: {silent['형식v1'][:4]}…, 전류_불일치 {[m[l].get('전류_불일치') for l in m]}")

        sql = {(r[0], r[1]) for r in con.execute(f"SELECT row_no, column_name FROM value_flag WHERE session_id = {sid0}")}
        df0 = pd.read_sql_query(f"SELECT * FROM sample WHERE session_id = {sid0} ORDER BY row_no", con)
        df0 = df0.rename(columns={c.lower(): c for c in db.COLUMNS})
        pf = verify.value_flags(df0, "v0_udp")             # SQL 과 같은 기준 (형식 전용 파일이 있으면 그것)
        pan = {(int(i) + 1, c.lower()) for c in pf.columns for i in np.flatnonzero(pf[c].to_numpy())}
        check("5. 시각 없는 형식에서도 값 검사 SQL = pandas", sql == pan and (2001, "fl") in sql,
              f"SQL {len(sql)}칸, pandas {len(pan)}칸, 심은 튐(2001행 fl) 잡음={(2001, 'fl') in sql}")

        tmp_vc = td / "value_check_v0_udp.csv"
        rows = list(csv.DictReader(open(db.VALUE_CHECK_CSV, encoding="utf-8")))
        for r in rows:
            if r["column_name"] == "fl":
                r["min_dev"], r["digit_min_dev"] = "1000", ""
        with open(tmp_vc, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
        orig = db.value_check_files
        db.value_check_files = lambda: {**orig(), "v0_udp": tmp_vc}
        try:
            db.refresh_flags(con)
            vcf = dict(con.execute("SELECT session_id, vc_format FROM temp.refresh_session").fetchall())
            hit = {s for (s,) in con.execute("SELECT session_id FROM value_flag WHERE row_no = 2001 AND column_name = 'fl'")}
            sql7 = {(r[0], r[1]) for r in con.execute(f"SELECT row_no, column_name FROM value_flag WHERE session_id = {sid0}")}
            pf7 = verify.value_flags(df0, "v0_udp")
            pan7 = {(int(i) + 1, c.lower()) for c in pf7.columns for i in np.flatnonzero(pf7[c].to_numpy())}
            check("7. 형식마다 값 검사 기준", vcf == {sid1: "v1_mcu", sid0: "v0_udp"} and hit == {sid1} and sql7 == pan7,
                  f"기준 {vcf}, 심은 튐을 잡은 세션 {hit} (v1 만이어야 함), v0 SQL = pandas {sql7 == pan7}")
        finally:
            db.value_check_files = orig
            db.refresh_flags(con)

        try:
            db.load_file(con, bad)
            check("6. 모르는 형식은 멈춤", False, "그냥 넣어짐")
        except ValueError as e:
            check("6. 모르는 형식은 멈춤", "모르는 로그 형식" in str(e), str(e)[:80])
        con.close()
    print("결과:", "통과" if not FAIL else f"실패 {FAIL}")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
