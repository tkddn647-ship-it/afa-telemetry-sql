"""세션 하나의 열마다 요약 (분석 에이전트가 '모든 열을 한 번씩' 보게 하려고 만든 도구, 2026-11-21).

blind 시험(eval_agent_blind.py)에서 에이전트가 이상 하나를 찾으면 조사를 멈추는 경우가 많았다.
열을 하나씩 SQL로 훑게 두는 대신, 흔한 데이터 품질 지표를 열마다 한 번에 준다 (Schelter 외 2018 의 열 프로파일과 같은 생각).
특정 이상 종류를 겨냥하지 않도록, 지표는 일반적인 것만 둔다:
  개수, 최소, 중앙값, 최대, 서로 다른 값 수, 0 비율,
  같은 값이 가장 오래 이어진 구간(0 이 아닌 값, 행 수·시작 행), 한 행 사이 가장 큰 변화(값·행).
깨진 행을 뺀 sample_clean 기준.
"""
from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd

SKIP = {"session_id", "row_no", "stm_ms"}


def profile(con: sqlite3.Connection, label: str) -> list[dict]:
    df = pd.read_sql_query(
        "SELECT c.* FROM sample_clean c JOIN session s USING (session_id) WHERE s.label = ? ORDER BY c.row_no",
        con, params=(label,))
    rows = df["row_no"].to_numpy()
    out = []
    for col in df.columns:
        if col in SKIP or not pd.api.types.is_numeric_dtype(df[col]):
            continue
        x = df[col].to_numpy(dtype=float)
        ok = ~np.isnan(x)
        if not ok.any():
            continue
        # 같은 값이 이어진 덩어리 (0 이 아닌 값만)
        change = np.concatenate([[True], x[1:] != x[:-1]])
        starts = np.flatnonzero(change)
        lens = np.diff(np.concatenate([starts, [len(x)]]))
        nz = x[starts] != 0
        if nz.any():
            k = int(np.argmax(np.where(nz, lens, 0)))
            run = {"rows": int(lens[k]), "value": float(x[starts[k]]), "first_row": int(rows[starts[k]]),
                   "last_row": int(rows[starts[k] + lens[k] - 1])}
        else:
            run = None
        d = np.abs(np.diff(x))
        j = int(np.nanargmax(d)) if len(d) and not np.isnan(d).all() else None
        out.append({
            "column": col, "n": int(ok.sum()),
            "min": float(np.nanmin(x)), "median": float(np.nanmedian(x)), "max": float(np.nanmax(x)),
            "distinct": int(pd.Series(x[ok]).nunique()), "zero_pct": round(100 * float((x[ok] == 0).mean()), 2),
            "longest_same_value_run": run,
            "largest_step": None if j is None else {"size": float(d[j]), "from_row": int(rows[j]), "to_row": int(rows[j + 1])},
        })
    return out
