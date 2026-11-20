"""숫자 글자 검사(sql/01a 의 digit_min_dev, 2026-11-21) 시험: 정상 행에 숫자 글자 손상을 심어 잡는 비율과 새 오탐을 잰다.

사용: python eval_digit.py   ->  eval/digit_report.md
분석용 3세션 x 시드 5개. 열(fr, fl, rr, rl, steering_angle)마다 위치 40개 (깨진 행·이미 표시된 행에서 5행 넘게 떨어진 곳).
심는 손상 (실제 로그에서 본 모양):
  끼어듦: 정수부 앞에 숫자 1~9 를 붙임   7.34 -> 27.34,  0.49 -> 20.49
  빠짐  : 정수부 첫 글자를 지움          15.59 -> 5.59,  -60.3 -> -0.3 (두 자리 이상일 때만)
  바뀜  : 정수부 첫 글자를 다른 숫자로    15.0 -> 55.0   (두 자리 이상일 때만)
판정은 pandas 구현(verify.value_flags, SQL 과 행 단위로 같음을 verify.py 가 확인)으로 하고, 숫자 글자 검사를 끈 것(예전 v2)과 비교한다.
"""
from __future__ import annotations

import random

import numpy as np
import pandas as pd

import db
import faults
import verify

COLS = sorted(verify.DIGIT_CHECK)
FILES = sorted((db.ROOT / "data").glob("*.csv.gz"))


def edit(v: float, kind: str, rng: random.Random) -> float | None:
    sign = "-" if v < 0 else ""
    s = f"{abs(v):.2f}".rstrip("0").rstrip(".") if abs(v) % 1 else f"{abs(v):.1f}"
    ip, _, fp = s.partition(".")
    if kind == "끼어듦":
        ip = str(rng.randint(1, 9)) + ip
    elif kind == "빠짐":
        if len(ip) < 2:
            return None
        ip = ip[1:]
    else:
        if len(ip) < 2:
            return None
        ip = str(rng.choice([d for d in range(1, 10) if str(d) != ip[0]])) + ip[1:]
    return float(sign + ip + ("." + fp if fp else ""))


def flags_with(df: pd.DataFrame, digit: bool) -> pd.DataFrame:
    keep = dict(verify.DIGIT_CHECK)
    if not digit:
        verify.DIGIT_CHECK.clear()
    try:
        return verify.value_flags(df)
    finally:
        verify.DIGIT_CHECK.clear()
        verify.DIGIT_CHECK.update(keep)


def main() -> None:
    res = {(c, k): [0, 0, 0, 0] for c in COLS for k in ("끼어듦", "빠짐", "바뀜")}   # 심음, 새 규칙 잡음, 예전 잡음, 기준 1배 이상
    fp_new = fp_old = 0
    rows_total = 0
    for f in FILES:
        base = faults.base_from(f)
        before_new = flags_with(base, True).any(axis=1).to_numpy()
        before_old = flags_with(base, False).any(axis=1).to_numpy()
        rows_total += len(base)
        for seed in range(5):
            rng = random.Random(seed * 100 + len(base))
            df = base.copy()
            low = {c.lower(): c for c in df.columns}
            busy = np.convolve(before_new.astype(int), np.ones(11, int), "same") > 0
            planted = []
            for c in COLS:
                col = low[c]
                cand = [i for i in range(10, len(df) - 10) if not busy[i]]
                for i in rng.sample(cand, 120):
                    if len([p for p in planted if p[1] == c]) >= 40:
                        break
                    if any(abs(i - p[0]) < 6 for p in planted):
                        continue
                    kind = ("끼어듦", "빠짐", "바뀜")[len([p for p in planted if p[1] == c]) % 3]
                    nv = edit(float(df.at[i, col]), kind, rng)
                    if nv is None or nv == df.at[i, col]:
                        continue
                    big = abs(nv - float(np.median(df[col].iloc[i - 2:i + 3]))) > verify.VALUE_CHECK[c]
                    df.at[i, col] = nv
                    planted.append((i, c, kind, big))
            fn = flags_with(df, True)
            fo = flags_with(df, False)
            for i, c, kind, big in planted:
                r = res[(c, kind)]
                r[0] += 1
                r[1] += bool(fn.at[i, c])
                r[2] += bool(fo.at[i, c])
                r[3] += big
            near = np.zeros(len(df), bool)
            for i, *_ in planted:
                near[max(0, i - 2): i + 3] = True
            fp_new += int((fn.any(axis=1).to_numpy() & ~near & ~before_new).sum())
            fp_old += int((fo.any(axis=1).to_numpy() & ~near & ~before_old).sum())
    lines = ["# 숫자 글자 검사 시험\n",
             "`python eval_digit.py` · 분석용 3세션 x 시드 5개, 열마다 위치 40개. 정상 행(깨진 행에서 5행 넘게 떨어진 곳)에 숫자 글자 손상을 심음.\n",
             "| 열 | 손상 | 심음 | 기준(범위 1배)을 넘는 것 | 예전 v2 잡음 | **숫자 글자 검사 추가** |", "|--|--|--|--|--|--|"]
    tot = [0, 0, 0, 0]
    for (c, k), r in res.items():
        if r[0]:
            lines.append(f"| {c} | {k} | {r[0]} | {r[3]} | {r[2]} ({100 * r[2] / r[0]:.0f}%) | **{r[1]} ({100 * r[1] / r[0]:.0f}%)** |")
            tot = [a + b for a, b in zip(tot, r)]
    lines.append(f"| 합계 | | {tot[0]} | {tot[3]} | {tot[2]} ({100 * tot[2] / tot[0]:.0f}%) | **{tot[1]} ({100 * tot[1] / tot[0]:.0f}%)** |")
    lines += ["", f"심은 자리에서 2행 넘게 떨어진 곳의 새 표시(오탐 후보): 예전 v2 {fp_old}행, 숫자 글자 검사 추가 {fp_new}행 "
                  f"(사본 {len(FILES) * 5}개, 각 약 {rows_total // len(FILES):,}행)",
              "", "실제 로그 10세션에 바로 적용하면 새로 표시되는 행은 9개 (서스펜션 7, 조향각 2). 예: 3.85 → 23.85 → 3.96, −60.3 → −0.3 → −60.3, 15.0 → 55.0 → 15.0."]
    (db.ROOT / "eval" / "digit_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
