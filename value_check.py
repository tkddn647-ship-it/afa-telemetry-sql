"""모든 숫자 열의 '튄 값' 검사: 기준표 만들기 + 결함 주입 평가 + 실제 로그에서 표시된 행 검토.

사용: python value_check.py --make     rules/value_check.csv 를 (다시) 만든다. 보통은 한 번만.
      python value_check.py            평가 -> eval/value_check_report.md

판정 (열마다, 같은 세션 안에서 row_no 순서로):
    |값 - 앞뒤 2행씩 5행의 중앙값| > min_dev  이고  그 값이 50 ms 이하로만 나타났으면 튄 값.
    5행이 다 있는 행만 판정 (세션 앞뒤 2행은 판정 안 함). 시각이 깨져 시간을 못 재면 행 수로만 판단.
  - 5행 창: 3행 이상 이어진 값은 창 안에서 다수가 되어 중앙값이 그 값이 된다 -> 1~2행만 나타난 값만 잡힌다.
    CAN 값은 약 10행(100 ms)마다 바뀌므로 1~2행짜리 값은 새 프레임일 수 없다.
    다만 샘플이 빠진 곳에서는 정상 프레임도 1~2행만 보일 수 있어(예: 2행이 120 ms), 실제 지속 시간 50 ms 이하만 잡는다.
  - min_dev (열마다, rules/value_check.csv):
      값이 유지되는 열 (CAN, 같은 값이 보통 9행 이상)    : 범위의 5%
      매 행 바뀌는 열 (서스펜션 변위, 조향)                 : 범위의 1배  (빠른 움직임은 정상이라 물리적으로 불가능한 크기만)
      가속도 (x_g, y_g, z_g)                                 : 범위의 2배  (노면 충격으로 한 행 튀는 게 정상)
    범위 = 분석용 3세션(지금 규칙이 깨졌다고 본 행 제외)의 1%~99% 분위 폭. 새 로그가 들어와도 다시 계산하지 않는다.
  - 처음엔 Hampel 필터(7행, 흔들림 MAD x 5 항 포함)였다. 실제 로그 1,351행 중 MAD 항이 바꾼 것은 5행뿐이었고
    그 5행도 손상 모양이라 뺐다. 7행 창은 3행 유지값(정상일 수 있음)까지 잡아서 5행으로 줄였다. (AI_LOG #15~17)
검사에서 뺀 열: stm_ms(시각은 sql/01 의 따로 규칙), 0/1 상태값 5개(얼마나 튀었는지 잴 수 없음).
"""
from __future__ import annotations

import argparse
import csv
import math
import random
from collections import Counter

import numpy as np
import pandas as pd

import db
import faults
from verify import value_flags

RULES = db.ROOT / "rules" / "value_check.csv"
SKIP = {"stm_ms", "motor_precharge", "motor_main_contactor", "motor_inverter_mode", "can1", "can2"}
CHECK = [c for c in db.COLUMNS if c not in SKIP]
FAST = {"FR", "FL", "RR", "RL", "steering_angle", "steering_speed"}
IMU = {"x_g", "y_g", "z_g"}
W = 5


def kind_of(c: str) -> tuple[str, float]:
    if c in IMU:
        return "가속도", 2.0
    if c in FAST:
        return "매 행 바뀜", 1.0
    return "값 유지", 0.05


def make() -> None:
    base = pd.concat([faults.base_from(f, rule="v1") for f in sorted((db.ROOT / "data").glob("*.csv.gz"))])   # 기준표를 만들 때 쓴 바탕 (v1)
    RULES.parent.mkdir(exist_ok=True)
    with open(RULES, "w", encoding="utf-8", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["column_name", "kind", "range_p1_p99", "multiple", "min_dev"])
        for c in CHECK:
            r = float(base[c].quantile(0.99) - base[c].quantile(0.01)) or 1.0      # 값이 하나뿐인 열은 1
            k, m = kind_of(c)
            wr.writerow([c.lower(), k, f"{r:.4g}", m, f"{r * m:.4g}"])
    print(RULES)


def load_rules() -> dict[str, float]:
    with open(RULES, encoding="utf-8") as fh:
        return {r["column_name"]: float(r["min_dev"]) for r in csv.DictReader(fh)}




def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def evaluate() -> None:
    rules = load_rules()
    md = {c: rules[c.lower()] for c in CHECK}
    buckets = [("기준 0.5배 미만", 0, 0.5), ("0.5~1배", 0.5, 1), ("1~2배", 1, 2), ("2배 이상", 2, 1e9)]
    files = sorted((db.ROOT / "data").glob("*.csv.gz"))
    hit = {(c, b[0], w): [0, 0] for c in CHECK for b in buckets for w in (1, 2)}
    extra = Counter()
    rows = 0
    for f in files:
        base = faults.base_from(f)
        before = value_flags(base)
        n = len(base)
        for seed in range(1, 6):
            rng = random.Random(seed)
            step = (n - 200) // 61
            pos = [100 + step * (j + 1) + rng.randrange(-step // 4, step // 4) for j in range(60)]
            rows += n
            df = base.copy()
            truth = {c: {} for c in CHECK}
            for c in CHECK:                       # 모든 열에 같은 위치, 열마다 크기는 따로
                x = df[c].astype(float).to_numpy().copy()
                for j, i in enumerate(pos):
                    rel = 10 ** rng.uniform(math.log10(0.1), 2)            # 기준의 0.1배 ~ 100배
                    w = 1 if j % 2 == 0 else 2
                    x[i:i + w] += rng.choice((-1, 1)) * rel * md[c]
                    truth[c][i] = (rel, w)
                df[c] = x
            vf = value_flags(df)                  # verify.py 의 판정 (SQL·리플레이와 행 단위로 같음을 확인한 것)
            for c in CHECK:
                fl = set(np.flatnonzero(vf[c.lower()].to_numpy()))
                spike = {i + k for i, (_, w) in truth[c].items() for k in range(w)}
                extra[c] += len(fl - spike - set(np.flatnonzero(before[c.lower()].to_numpy())))
                for i, (rel, w) in truth[c].items():
                    for name, lo, hi in buckets:
                        if lo <= rel < hi:
                            hit[(c, name, w)][1] += 1
                            hit[(c, name, w)][0] += any(i + k in fl for k in range(w))

    lines = ["# 모든 숫자 열의 튄 값 검사\n",
             "`python value_check.py` · 판정: |값 − 앞뒤 2행씩 5행 중앙값| > min_dev ([`rules/value_check.csv`](../rules/value_check.csv)), "
             "그리고 그 값이 50 ms 이하로만 나타남 (sql/01a)\n",
             "## 1. 결함 주입: 탐지율\n",
             f"분석용 3세션 x 시드 5개 x 위치 60개, 열 {len(CHECK)}개. 크기 = 기준(min_dev)의 0.1~100배, 절반은 두 행 연속. "
             "기준값을 이 시험으로 고르지 않았으므로 조정용·시험용을 나누지 않음.\n",
             "| 열 | 종류 | min_dev | " + " | ".join(f"{b[0]} (1행/2행)" for b in buckets) + " | 엉뚱한 행 표시 |",
             "|--|--|--|" + "--|" * (len(buckets) + 1)]
    tot = Counter()
    for c in CHECK:
        cells = []
        for b in buckets:
            h1, h2 = hit[(c, b[0], 1)], hit[(c, b[0], 2)]
            cells.append(f"{h1[0]}/{h1[1]} · {h2[0]}/{h2[1]}")
            for w, h in ((1, h1), (2, h2)):
                tot[(b[0], w, 0)] += h[0]; tot[(b[0], w, 1)] += h[1]
        lines.append(f"| {c} | {kind_of(c)[0]} | {md[c]:g} | " + " | ".join(cells) + f" | {extra[c]} |")
    lines.append("| **전체** | | | " + " | ".join(
        f"**{tot[(b[0], 1, 0)]}/{tot[(b[0], 1, 1)]} · {tot[(b[0], 2, 0)]}/{tot[(b[0], 2, 1)]}**" for b in buckets)
        + f" | **{sum(extra.values())}** |")
    lines += ["", f"검사한 행: 열마다 {rows:,}개. '엉뚱한 행 표시' = 심기 전에는 표시 안 됐는데 심은 뒤 튐이 아닌 행이 새로 표시된 수.", ""]

    # 2. 실제 로그 검토 (DB의 value_flag 표 = SQL 판정)
    con = db.connect_readonly()
    n_all = con.execute("SELECT COUNT(*) FROM sample").fetchone()[0]
    per_col, flagged_rows = Counter(), {}
    for label, r, c, v, m in con.execute("SELECT s.label, f.row_no, f.column_name, f.value, f.median5 FROM value_flag f "
                                         "JOIN session s USING (session_id) ORDER BY f.session_id, f.row_no"):
        flagged_rows.setdefault((label, r), []).append((c, v, m))
        per_col[c] += 1
    cols = [c.lower() for c in CHECK]
    cat = Counter()
    other = []
    for key, items in flagged_rows.items():
        if len(items) >= 3:
            cat["행 손상 (같은 행에서 3열 이상)"] += 1
            continue
        digit = all(edit_distance(f"{v:g}", f"{m:g}") <= 2 for _, v, m in items)
        if digit:
            cat["숫자 글자 1~2개 차이 (예: 267.3 → 27.3)"] += 1
        else:
            cat["그 밖 (사람 확인)"] += 1
            other.append((key, items))
    total = len(flagged_rows)
    lines += ["## 2. 실제 로그 10세션에서 표시된 행\n",
              f"표시된 행 {total:,}개 / 전체 {n_all:,}행 ({100 * total / n_all:.2f}%). 정답이 없어서 모양으로 나눴다 (자동 분류).\n",
              "| 모양 | 행 수 | 비율 |", "|--|--|--|"]
    for k in ("행 손상 (같은 행에서 3열 이상)", "숫자 글자 1~2개 차이 (예: 267.3 → 27.3)", "그 밖 (사람 확인)"):
        lines.append(f"| {k} | {cat[k]} | {100 * cat[k] / total:.1f}% |")
    lines += ["", "앞의 두 모양은 전송 중 손상으로 볼 근거가 강하다. '그 밖'은 정상 값일 수도 있어 아래에 전부 적는다.", "",
              "| 세션 | 행 | 열: 값 (5행 중앙값) |", "|--|--|--|"]
    for (label, r), items in other:
        lines.append(f"| {label} | {r} | " + ", ".join(f"{c}: {v:g} ({m:g})" for c, v, m in items) + " |")
    lines += ["", "## 3. 열별 표시 수 (실제 로그)\n", "| 열 | 표시된 행 |", "|--|--|"]
    lines += [f"| {c} | {per_col[c]} |" for c in cols]
    (db.ROOT / "eval" / "value_check_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:60]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--make", action="store_true")
    a = ap.parse_args()
    if a.make:
        make()
    evaluate()
