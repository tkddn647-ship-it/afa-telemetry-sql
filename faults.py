"""로그에 결함을 '정답과 함께' 심는다. 품질 규칙이 실제로 몇 개를 잡는지 재기 위한 도구.

사용: python faults.py data/sensor_log_20260811_오후2차.csv.gz --seed 1 --out faulted/
결과: faulted/<원본이름>_seed1.csv.gz  +  같은 이름의 .truth.json (어느 행에 무슨 결함을 넣었는지)

바탕 데이터: 원본에서 이미 깨진 것으로 표시된 행을 먼저 뺀다 (그래야 '규칙이 잡은 것 중 정답이 아닌 것' = 오탐으로 셀 수 있다).
심는 결함 (실제 로그에서 본 모양을 흉내 냄):
  ts_drop    시각 숫자 한 글자가 빠짐         (예: 345982 -> 35982)
  ts_insert  시각에 숫자가 끼어듦             (예: 377212 -> 37721243)
  ts_pair    깨진 시각이 두 행 연달아         (오후1차 11419·11420행 모양)
  spike_inv  인버터 전류 한 행이 튐  (+20~1000 A, 규칙 기준 200 A보다 작은 것도 일부러 섞음)
  spike_bms  팩 전류 한 행이 튐     (+10~500 A, 기준 100 A)
  spike_speed 속도 한 행이 튐       (+5~5000 km/h, 기준 30 km/h)
  drop_burst 연속 k행이 통째로 빠짐            (행 정답 대신 빠진 샘플 수로 채점)
  restart    MCU 재시작: 시계가 작은 값부터 다시 셈
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import math
import random
from pathlib import Path

import pandas as pd

from verify import flags

COUNTS = {"ts_drop": 20, "ts_insert": 20, "ts_pair": 10, "spike_inv": 15, "spike_bms": 15,
          "spike_speed": 15, "drop_burst": 10, "restart": 2}
SPIKE = {"spike_inv": ("inv_dc_current", 20, 1000), "spike_bms": ("bms_current", 10, 500),
         "spike_speed": ("vehicle_speed_kmh", 5, 5000)}
THRESHOLD = {"spike_inv": 200, "spike_bms": 100, "spike_speed": 30}   # sql/01_flags.sql 의 기준
GAP = 30  # 결함끼리 최소 이만큼 떨어뜨린다 (서로 이웃이 되면 규칙이 헷갈려서 채점이 불공정해짐)


def _drop_digit(v: int, rng: random.Random) -> int:
    s = str(v)
    i = rng.randrange(1, len(s))          # 맨 앞 자리는 남김
    return int(s[:i] + s[i + 1:])


def _insert_digits(v: int, rng: random.Random) -> int:
    s = str(v)
    i = rng.randrange(1, len(s) + 1)
    return int(s[:i] + str(rng.randrange(10, 100)) + s[i:])


def inject(df: pd.DataFrame, rng: random.Random) -> tuple[pd.DataFrame, dict]:
    df = df.reset_index(drop=True).copy()
    n = len(df)
    # 결함 위치 고르기: 서로 GAP 이상 떨어지고, 양끝 100행은 피한다
    kinds = [k for k, c in COUNTS.items() for _ in range(c)]
    rng.shuffle(kinds)
    slots, pos = [], 100
    usable = n - 200
    step = usable // (len(kinds) + 1)
    if step < GAP:
        raise SystemExit("로그가 너무 짧음")
    for _ in kinds:
        pos += step
        slots.append(pos + rng.randrange(-step // 4, step // 4))
    plan = sorted(zip(slots, kinds))

    truth_rows: list[tuple[int, str]] = []   # (원본 인덱스, 종류)
    sizes: dict[int, float] = {}
    drop_idx: list[int] = []
    dropped_samples = 0
    restarts = 0
    stm = df["stm_ms"].astype("int64")
    for i, kind in plan:
        if kind == "ts_drop":
            stm.iat[i] = _drop_digit(int(stm.iat[i]), rng); truth_rows.append((i, kind))
        elif kind == "ts_insert":
            stm.iat[i] = _insert_digits(int(stm.iat[i]), rng); truth_rows.append((i, kind))
        elif kind == "ts_pair":
            stm.iat[i] = _insert_digits(int(stm.iat[i]), rng)
            stm.iat[i + 1] = _drop_digit(int(stm.iat[i + 1]), rng)
            truth_rows += [(i, kind), (i + 1, kind)]
        elif kind in SPIKE:
            col, lo, hi = SPIKE[kind]
            size = round(10 ** rng.uniform(math.log10(lo), math.log10(hi)), 1)   # 작은 것부터 큰 것까지 고르게(로그 척도)
            df.at[i, col] = df.at[i, col] + size
            truth_rows.append((i, kind)); sizes[i] = size
        elif kind == "drop_burst":
            k = rng.randrange(2, 21)
            drop_idx += list(range(i, i + k)); dropped_samples += k
        elif kind == "restart":
            # i행부터 시계를 (현재값 - 작은값)만큼 당긴다: 이후 값은 계속 10 ms씩 늘지만 i에서 한 번 크게 줄어듦
            offset = int(stm.iat[i]) - rng.randrange(30_000, 60_000)
            if offset > 1000:
                stm.iloc[i:] = stm.iloc[i:] - offset
                restarts += 1
    df["stm_ms"] = stm
    marked = pd.Series("", index=df.index)
    size_col = pd.Series(float("nan"), index=df.index)
    for i, kind in truth_rows:
        marked.iat[i] = kind
        if i in sizes:
            size_col.iat[i] = sizes[i]
    df["_truth"], df["_size"] = marked, size_col
    df = df.drop(index=drop_idx).reset_index(drop=True)
    truth = {
        "rows": [{"row_no": int(r) + 1, "kind": k, **({"size": df.at[r, "_size"]} if k in SPIKE else {})}
                 for r, k in df["_truth"].items() if k],
        "dropped_samples": dropped_samples,
        "restarts": restarts,
        "counts": COUNTS,
    }
    return df.drop(columns=["_truth", "_size"]), truth


def base_from(path: Path) -> pd.DataFrame:
    """원본에서 이미 깨진 것으로 표시된 행을 뺀 바탕 데이터."""
    df = pd.read_csv(path, dtype={"timestamp": str})
    bad = flags(df).any(axis=1)
    return df[~bad].reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", type=Path, default=Path("faulted"))
    a = ap.parse_args()
    a.out.mkdir(exist_ok=True)
    df, truth = inject(base_from(a.src), random.Random(a.seed))
    stem = a.src.name.replace(".csv.gz", "")
    out = a.out / f"{stem}_seed{a.seed}.csv.gz"
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    with gzip.open(out, "wt", encoding="utf-8", newline="") as fh:
        fh.write(buf.getvalue())
    (a.out / f"{stem}_seed{a.seed}.truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=1), encoding="utf-8")
    print(out, f"결함 행 {len(truth['rows'])}개, 빠뜨린 샘플 {truth['dropped_samples']}개, 재시작 {truth['restarts']}번")


if __name__ == "__main__":
    main()


def inject_stuck(df: pd.DataFrame, rng: random.Random, col: str = "inv_dc_current", length: int = 300) -> tuple[pd.DataFrame, dict]:
    """품질 규칙에 없는 이상 하나: 주행 중 한 신호가 length행 동안 같은 값에 멈춤 (센서·통신 고착).
    분석 에이전트가 규칙에 없는 이상도 찾는지 보려고 쓴다. 정답 = 멈춘 행 범위."""
    df = df.reset_index(drop=True).copy()
    moving = df.index[(df["vehicle_speed_kmh"] > 20) & (df[col] > 25)]
    for _ in range(1000):
        start = int(rng.choice(list(moving)))
        seg = df.loc[start:start + length - 1]
        if len(seg) == length and (seg["vehicle_speed_kmh"] > 5).all() and seg[col].std() > 5:
            break
    else:
        raise SystemExit("멈춤을 넣을 주행 구간을 못 찾음")
    df.loc[start:start + length - 1, col] = df.at[start, col]
    return df, {"kind": "stuck", "column": col, "first_row": start + 1, "last_row": start + length}
