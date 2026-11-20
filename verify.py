"""SQL 결과를 pandas로 따로 계산해 맞는지 확인한다 (같은 숫자가 두 방법에서 나와야 통과).

사용: python verify.py
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

import db

ROOT = Path(__file__).parent
FILES = sorted((ROOT / "data").glob("*.csv.gz"))


VALUE_CHECK = {r["column_name"]: float(r["min_dev"])
               for r in csv.DictReader(open(ROOT / "rules" / "value_check.csv", encoding="utf-8"))}


def value_flags(df: pd.DataFrame) -> pd.DataFrame:
    """sql/01a 와 같은 판정을 pandas로: |값 - 앞뒤 2행씩 5행 중앙값| > min_dev. 열 이름은 소문자."""
    low = {c.lower(): c for c in df.columns}
    t = df[low["stm_ms"]].astype(float)
    out = pd.DataFrame(index=df.index)
    for col, md in VALUE_CHECK.items():
        x = df[low[col]].astype(float)
        med = x.rolling(5, center=True, min_periods=5).median()
        # 그 값이 실제로 나타난 시간 (sql/01a 와 같은 정의)
        dur = np.where(x == x.shift(-1), t.shift(-2) - t, np.where(x == x.shift(1), t.shift(-1) - t.shift(1), t.shift(-1) - t))
        dur = pd.Series(dur, index=df.index)
        short = dur.isna() | (dur <= 50) | (dur < 0) | (dur > 1000)
        out[col] = ((x - med).abs() > md).fillna(False) & short
    return out


def flags(df: pd.DataFrame, rule: str = "v2") -> pd.DataFrame:
    """rule='v1': 2026-11-20 전 규칙 (값은 인버터·팩·속도 3열만 앞뒤 한 행 비교). 'v2': 지금 규칙 (sql/01_flags.sql)."""
    def spike(col: str, big: float, near: float) -> pd.Series:
        x, p, n = df[col], df[col].shift(1), df[col].shift(-1)
        return ((x - p).abs() > big) & ((x - n).abs() > big) & ((n - p).abs() < near)
    s = df.stm_ms
    p, n, p2, n2 = s.shift(1), s.shift(-1), s.shift(2), s.shift(-2)
    out = pd.DataFrame(index=df.index)
    out["bad_ms"] = (((s - p).abs() > 1000) & ((s - n).abs() > 1000) & (n - p).between(0, 200)) \
        | (((s - p).abs() > 1000) & ((s - n2).abs() > 1000) & (n2 - p).between(0, 300)) \
        | (((s - p2).abs() > 1000) & ((s - n).abs() > 1000) & (n - p2).between(0, 300))
    out["bad_inv"] = spike("inv_dc_current", 200, 100)
    out["bad_bms"] = spike("bms_current", 100, 50)
    out["bad_speed"] = spike("vehicle_speed_kmh", 30, 15)
    if rule == "v1":
        return out
    vf = value_flags(df)
    out["bad_inv"] |= vf["inv_dc_current"]
    out["bad_bms"] |= vf["bms_current"]
    out["bad_speed"] |= vf["vehicle_speed_kmh"]
    out["bad_value"] = vf.any(axis=1)
    return out


def python_numbers() -> dict:
    res = {}
    for f in FILES:
        i = db.label_of(f)
        df = pd.read_csv(f)
        fl = flags(df)
        load = df.inv_dc_current > 25
        r = df.bms_current / df.inv_dc_current
        res[(i, "median")] = round(r[load].median(), 3)

        ok = load & ~fl.bad_inv & ~fl.bad_bms
        a, b = np.polyfit(df.inv_dc_current[ok], df.bms_current[ok], 1)
        res[(i, "slope")] = round(a, 3)

        res[(i, "broken")] = int(fl.any(axis=1).sum())

        clean = df[~fl.bad_ms]
        d = clean.stm_ms.diff()
        skipped = pd.Series(clean.index, index=clean.index).diff() - 1   # 그 사이에 뺀 깨진 시각 행 수
        m = ((d / 10).round() - 1 - skipped).clip(lower=0)
        res[(i, "missed")] = float(m[(d > 15) & (d <= 1000)].sum())

        inv, bms = df.inv_dc_current[ok], df.bms_current[ok]
        res[(i, "viol_after")] = round(100 * (inv > 1.05 * bms * 1.25).mean(), 1)

        # 여러 신호 검사 (sql/10 과 같은 정의를 pandas로): 깨진 행을 뺀 뒤
        cl = df[~fl.any(axis=1)].copy()
        cl["row_no"] = cl.index + 1
        mc = cl.motor_main_contactor
        close = cl[(mc == 1) & (mc.shift(1) == 0)]
        ratio = close.inv_voltage / close.bms_voltage
        res[(i, "closures")] = len(close)
        res[(i, "precharge_bad")] = int((ratio < 0.90).sum())   # KSAE 제52조 ①
        m = (cl.inv_dc_current > 25) & (cl.bms_current <= 0.5)
        r = cl.row_no[m]
        grp = (r.diff() != 1).cumsum()                     # 행 번호가 1씩 이어지는 덩어리
        res[(i, "mismatch")] = int((r.groupby(grp).size() >= 10).sum())
        res[(i, "open_current")] = int(((mc == 0) & (cl.inv_dc_current.abs() > 5)).sum())
    return res


def sql_numbers() -> dict:
    con = sqlite3.connect(ROOT / "telemetry.db")
    q = lambda name: con.execute((ROOT / "sql" / name).read_text(encoding="utf-8")).fetchall()
    res = {}
    for row in q("02_ratio_median.sql"):
        i = row[0]
        res[(i, "median")] = row[2]
    for row in q("03_scale_or_offset.sql"):
        i = row[0]
        res[(i, "slope")] = row[2]
    for row in q("05_broken_rows.sql"):
        i = row[0]
        res[(i, "broken")] = row[8]
    for row in q("06_sample_loss.sql"):
        i = row[0]
        res[(i, "missed")] = row[2]
    for row in q("07_physics_check.sql"):
        i = row[0]
        res[(i, "viol_after")] = row[3]
    for row in q("10_cross_signal.sql"):
        i = row[0]
        res[(i, "closures")], res[(i, "precharge_bad")], res[(i, "mismatch")], res[(i, "open_current")] = row[1], row[3], row[4], row[6]
    return res


def value_flag_rows() -> int:
    """value_flag 표(SQL)와 pandas 판정이 (세션, 행, 열) 단위로 같은지. 10개 세션 전부."""
    con = sqlite3.connect(ROOT / "telemetry.db")
    bad = 0
    for sid, label, fname in con.execute("SELECT session_id, label, file_name FROM session ORDER BY session_id").fetchall():
        path = next((p for d in ("data", "inbox") for p in [ROOT / d / fname] if p.exists()), None)
        if path is None:
            continue
        vf = value_flags(pd.read_csv(path))
        py = {(int(r) + 1, c) for c in vf.columns for r in np.flatnonzero(vf[c].to_numpy())}
        sq = set(con.execute("SELECT row_no, column_name FROM value_flag WHERE session_id = ?", (sid,)).fetchall())
        same = py == sq
        bad += not same
        print(f"{'OK ' if same else 'DIFF'} {label} value_flag  python={len(py)}  sql={len(sq)}")
    return bad


def main() -> None:
    py, sq = python_numbers(), sql_numbers()
    bad = value_flag_rows()
    for k in sorted(py):
        if k not in sq:
            continue
        same = abs(py[k] - sq[k]) < 1e-9 if isinstance(py[k], float) else py[k] == sq[k]
        bad += not same
        print(f"{'OK ' if same else 'DIFF'} {k[0]} {k[1]:<10} python={py[k]}  sql={sq[k]}")
    print("\n모두 일치" if bad == 0 else f"\n불일치 {bad}건")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
