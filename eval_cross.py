"""여러 신호 검사(sql/10, REQ-14~16)가 맞게 판정하는지, 실제 로그를 고친 사본으로 시험한다.

사용: python eval_cross.py   ->  eval/cross_report.md
실제 적재 경로(파일 -> DB -> 값 검사 -> sql/10)를 그대로 쓴다. 정답은 고친 방식에서 정해진다.

  A. 프리차지 경계: 실제 접촉기 닫힘 행부터 10행 동안 인버터 전압을 팩 전압 x X 로 바꾼다 (10행 유지라 값 검사가 빼지 않음).
     X = 0.85, 0.89, 0.899, 0.90, 0.901, 0.91, 0.95 와 고치지 않은 원본. 정답: X >= 0.90 이면 통과, 아니면 미달 (KSAE 제52조 ①).
     (처음엔 닫힘 행을 옮겼는데, 실제 로그의 인버터 전압은 CAN 갱신 때문에 81% 에서 101% 로 바로 뛰어 경계를 시험하지 못했다)
  B. 전류 끊김: 부하 중(인버터 > 25 A, 팩 > 5 A)인 곳에서 팩 전류를 k행 동안 -1.5 A 로 바꾼다.
     k = 3, 5, 8, 9, 10, 11, 15, 30. 정답: k >= 10 이면 불일치 1번, 아니면 0번.
     (k = 1~2 는 값 검사가 튄 값으로 먼저 빼므로 시험하지 않는다)
  C. 접촉기 열림 중 전류: 부하 중인 곳에서 접촉기 신호를 k행 동안 0 으로 바꾼다. k = 1, 2, 3, 5, 10, 30.
     정답: 그 k행이 모두 '열림 중 전류' 로 잡힘. 접촉기 신호는 값 검사에서 빼는 상태값이라 k = 1 도 남는다.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

import db
from eval_detection import write_gz
from verify import flags

SQL10 = (db.ROOT / "sql" / "10_cross_signal.sql").read_text(encoding="utf-8")
FILES = sorted((db.ROOT / "data").glob("*.csv.gz"))
COLS = ["세션", "접촉기_닫힘", "닫힐때_전압비_최소", "프리차지_미달", "전류_불일치", "불일치_최장_행", "열림중_전류_행"]


def run_sql10(df: pd.DataFrame) -> dict:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "sensor_log_00000000_x.csv.gz"
        write_gz(df, p)
        con = db.create(Path(td) / "t.db")
        db.load_file(con, p)
        db.refresh_flags(con)
        row = con.execute(SQL10).fetchone()
        con.close()
    return dict(zip(COLS, row))


def load_rows(df: pd.DataFrame, k: int, n: int, gap: int = 400) -> list[int]:
    """부하가 k+20행 넘게 이어지고 깨진 행이 없는 곳의 시작 위치 n개 (서로 gap 이상 떨어짐).
    깨진 행은 판정에서 빠지므로, 그 위에 심으면 정답 계산이 어긋난다 (처음 버전에서 51 대 50)."""
    ok = ((df.inv_dc_current > 25) & (df.bms_current > 5) & ~flags(df).any(axis=1)).to_numpy()
    out, i = [], 200
    while i < len(df) - k - 200 and len(out) < n:
        if ok[i:i + k + 20].all() and (not out or i - out[-1] >= gap):
            out.append(i + 10)
            i += gap
        else:
            i += 1
    return out


def main() -> None:
    lines = ["# 여러 신호 검사 시험 (REQ-14~16)\n",
             "`python eval_cross.py` · 실제 로그(분석용 3세션)를 고친 사본을 실제 적재 경로(파일 → DB → 값 검사 → `sql/10`)로 판정.\n"]

    # A. 프리차지 경계
    lines += ["## A. 프리차지 경계 (닫히는 순간의 전압을 바꿈)\n", "| 세션 | 닫힐 때 비율 | 정답 | 판정 | 맞음 |", "|--|--|--|--|--|"]
    a_ok = a_n = 0
    for f in FILES:
        base = pd.read_csv(f, dtype={"timestamp": str})
        label = f.name.split("_")[-1][:-7]
        mc = base.motor_main_contactor.to_numpy()
        up = np.flatnonzero((mc[1:] == 1) & (mc[:-1] == 0)) + 1
        bad = flags(base).any(axis=1).to_numpy()
        up = [int(j) for j in up if not bad[j - 1: j + 11].any()]   # 깨진 행 옆이 아닌 진짜 닫힘
        if not up:
            continue
        j = up[0]
        for x in (None, 0.85, 0.89, 0.899, 0.90, 0.901, 0.91, 0.95):
            df = base.copy()
            if x is not None:
                df.loc[j: j + 9, "inv_voltage"] = (df.loc[j: j + 9, "bms_voltage"] * x).round(2)
            ratio = df.inv_voltage[j] / df.bms_voltage[j]
            r = run_sql10(df)
            want_bad = ratio < 0.90
            got_bad = r["프리차지_미달"] > 0
            a_n += 1
            a_ok += want_bad == got_bad
            lines.append(f"| {label} | {ratio:.5f}{' (원본)' if x is None else ''} | {'미달' if want_bad else '통과'} | "
                         f"{'미달' if got_bad else '통과'} (닫힘 {r['접촉기_닫힘']}번) | {'O' if want_bad == got_bad else 'X'} |")
    lines += ["", f"맞음 {a_ok}/{a_n}. 비율은 전압을 0.01 V로 반올림한 뒤 값이라 0.90 목표가 0.89998 이 되기도 함 (판정은 그 값 기준).", ""]

    # B, C. 한 사본에 여러 군데 심는다
    ks_b = [3, 5, 8, 9, 10, 11, 15, 30]
    ks_c = [1, 2, 3, 5, 10, 30]
    b_rows = ["## B. 팩 전류 끊김 (k행 동안 -1.5 A)\n", "| 세션 | 심은 k | 정답 불일치 | 판정 불일치 | 가장 긴 불일치 | 맞음 |", "|--|--|--|--|--|--|"]
    c_rows = ["## C. 접촉기 열림 중 전류 (k행 동안 접촉기 0)\n", "| 세션 | 심은 k | 정답 행 | 판정 행 | 맞음 |", "|--|--|--|--|--|"]
    b_ok = b_n = c_ok = c_n = 0
    for f in FILES:
        base = pd.read_csv(f, dtype={"timestamp": str})
        label = f.name.split("_")[-1][:-7]
        before = run_sql10(base)
        for k in ks_b:                                  # k 마다 따로 판정 (서로 섞이지 않게)
            df = base.copy()
            pos = load_rows(df, k, 1)
            if not pos:
                continue
            i = pos[0]
            df.loc[i: i + k - 1, "bms_current"] = -1.5
            r = run_sql10(df)
            want = before["전류_불일치"] + (1 if k >= 10 else 0)
            b_n += 1
            b_ok += r["전류_불일치"] == want
            b_rows.append(f"| {label} | {k} | {want} | {r['전류_불일치']} | {r['불일치_최장_행']} | {'O' if r['전류_불일치'] == want else 'X'} |")
        df = base.copy()
        pos = load_rows(df, max(ks_c), len(ks_c))
        injected = 0
        for k, i in zip(ks_c, pos):
            df.loc[i: i + k - 1, "motor_main_contactor"] = 0
            injected += k
        r = run_sql10(df)
        want = before["열림중_전류_행"] + injected
        c_n += 1
        c_ok += r["열림중_전류_행"] == want
        c_rows.append(f"| {label} | {', '.join(map(str, ks_c))} (합 {injected}) | {want} | {r['열림중_전류_행']} | {'O' if r['열림중_전류_행'] == want else 'X'} |")
    lines += b_rows + ["", f"맞음 {b_ok}/{b_n} (원래 로그에 있던 불일치 수를 더해 정답을 정함)", ""]
    lines += c_rows + ["", f"맞음 {c_ok}/{c_n}", ""]
    (db.ROOT / "eval" / "cross_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
