"""SQL 결과를 pandas로 따로 계산해 맞는지 확인한다 (같은 숫자가 두 방법에서 나와야 통과).

사용: python verify.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
FILES = sorted((ROOT / "data").glob("*.csv.gz"))


def flags(df: pd.DataFrame) -> pd.DataFrame:
    def spike(col: str, big: float, near: float) -> pd.Series:
        x, p, n = df[col], df[col].shift(1), df[col].shift(-1)
        return ((x - p).abs() > big) & ((x - n).abs() > big) & ((n - p).abs() < near)
    p, n = df.stm_ms.shift(1), df.stm_ms.shift(-1)
    out = pd.DataFrame(index=df.index)
    out["bad_ms"] = ((df.stm_ms - p).abs() > 1000) & ((df.stm_ms - n).abs() > 1000) & (n - p).between(0, 200)
    out["bad_inv"] = spike("inv_dc_current", 200, 100)
    out["bad_bms"] = spike("bms_current", 100, 50)
    out["bad_speed"] = spike("vehicle_speed_kmh", 30, 15)
    return out


def python_numbers() -> dict:
    res = {}
    for i, f in enumerate(FILES, start=1):
        df = pd.read_csv(f)
        fl = flags(df)
        load = df.inv_dc_current > 25
        r = df.bms_current / df.inv_dc_current
        res[(i, "median")] = round(r[load].median(), 3)

        ok = load & ~fl.bad_inv & ~fl.bad_bms
        a, b = np.polyfit(df.inv_dc_current[ok], df.bms_current[ok], 1)
        res[(i, "slope")] = round(a, 3)

        res[(i, "broken")] = int(fl.any(axis=1).sum())

        d = df.stm_ms[~fl.bad_ms].diff()
        res[(i, "missed")] = float(((d[(d > 15) & (d <= 1000)] / 10).round() - 1).sum())

        inv, bms = df.inv_dc_current[ok], df.bms_current[ok]
        res[(i, "viol_after")] = round(100 * (inv > 1.05 * bms * 1.25).mean(), 1)
    return res


def sql_numbers() -> dict:
    con = sqlite3.connect(ROOT / "telemetry.db")
    con.executescript((ROOT / "sql" / "01_flags.sql").read_text(encoding="utf-8"))
    q = lambda name: con.execute((ROOT / "sql" / name).read_text(encoding="utf-8")).fetchall()
    res = {}
    for i, row in enumerate(q("02_ratio_median.sql"), start=1):
        res[(i, "median")] = row[2]
    for i, row in enumerate(q("03_scale_or_offset.sql"), start=1):
        res[(i, "slope")] = row[2]
    for i, row in enumerate(q("05_broken_rows.sql"), start=1):
        res[(i, "broken")] = row[6]
    for i, row in enumerate(q("06_sample_loss.sql"), start=1):
        res[(i, "missed")] = row[2]
    for i, row in enumerate(q("07_physics_check.sql"), start=1):
        res[(i, "viol_after")] = row[3]
    return res


def main() -> None:
    py, sq = python_numbers(), sql_numbers()
    bad = 0
    for k in sorted(py):
        same = abs(py[k] - sq[k]) < 1e-9 if isinstance(py[k], float) else py[k] == sq[k]
        bad += not same
        print(f"{'OK ' if same else 'DIFF'} 세션{k[0]} {k[1]:<10} python={py[k]}  sql={sq[k]}")
    print("\n모두 일치" if bad == 0 else f"\n불일치 {bad}건")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
