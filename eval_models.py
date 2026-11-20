"""튄 값 탐지: 지금 규칙 vs 기준을 낮춘 규칙 vs 통계 필터(Hampel) vs 머신러닝(Isolation Forest).

사용: python eval_models.py   ->  eval/models_report.md
질문: 규칙 기준(인버터 200 A, 팩 100 A, 속도 30 km/h)보다 작은 튐을 잡으려면 모델이 필요한가, 기준만 낮추면 되나?

공정하게 비교하려고 지킨 것
  1. 튄 값만 심는다 (행을 빼거나 넣지 않음). 그래야 바탕 데이터와 행 번호가 같아서 '원래 있던 것'을 따로 셀 수 있다.
  2. 바탕 데이터에도 정답 표시가 없는 진짜 이상이 남아 있다 (예: 44.4 -> 4.4 -> 44.4 A).
     결함을 심기 전 바탕에서 어느 방법이든 표시한 행은 '정답 모름'으로 빼고 채점하고, 따로 표로 보여 준다.
  3. 방법마다 점수 하나를 내고 기준값을 바꿔 가며 잰다. 기준값은 시드 1~3(조정용)에서 정하고 시드 4~6(시험용)에서 잰다.
     비교는 '오탐을 같은 수준으로 맞췄을 때 얼마나 잡나'로 한다.
  4. 바탕 데이터는 지금 규칙이 깨졌다고 본 행을 뺀 것이라, 지금 규칙의 오탐 0은 구조상 당연하다. 그래서 오탐 0 자체는 장점으로 세지 않는다.
"""
from __future__ import annotations

import math
import random

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

import json

import db
import faults
from verify import flags

COLS = {"inv_dc_current": (20, 1000, 200, 100), "bms_current": (10, 500, 100, 50),
        "vehicle_speed_kmh": (5, 5000, 30, 15)}          # 심을 크기 범위, 지금 규칙의 기준(큰 차이, 앞뒤 근접)
BUCKETS = [("기준 0.5배 미만", 0, 0.5), ("0.5~1배", 0.5, 1.0), ("1~2배", 1.0, 2.0), ("2배 이상", 2.0, 1e9)]
PER_COL = 60          # 한 번에 열마다 심는 튐 수
TUNE, TEST = (1, 2, 3), (4, 5, 6)
BUDGET = 1.0          # 허용 오탐: 1만 행당 이 수 이하


# ---------- 점수: 클수록 이상 ----------
def score_rule(x: pd.Series) -> np.ndarray:
    """지금 규칙의 모양(앞뒤 둘 다와 멀고, 앞뒤끼리는 가까움)을 점수로. 기준값을 낮추면 '기준을 낮춘 규칙'."""
    dp, dn, pn = (x - x.shift(1)).abs(), (x - x.shift(-1)).abs(), (x.shift(-1) - x.shift(1)).abs()
    d = np.minimum(dp, dn)
    return np.where(pn < 0.5 * d, d, 0.0)


def score_hampel(x: pd.Series, floor: float = 1.0) -> np.ndarray:
    med = x.rolling(7, center=True, min_periods=3).median()
    mad = (x - med).abs().rolling(7, center=True, min_periods=3).median()
    return ((x - med).abs() / np.maximum(1.4826 * mad, floor)).to_numpy()


def score_iforest(x: pd.Series, seed: int) -> np.ndarray:
    med = x.rolling(7, center=True, min_periods=3).median()
    f = np.c_[(x - x.shift(1)).fillna(0), (x - x.shift(-1)).fillna(0), (x - med).fillna(0)]
    return -IsolationForest(n_estimators=100, random_state=seed).fit(f).score_samples(f)


METHODS = {"기준 낮춘 규칙": lambda x, s: score_rule(x), "Hampel": lambda x, s: score_hampel(x),
           "IForest": score_iforest}


def inject_spikes(base: pd.DataFrame, rng: random.Random) -> tuple[pd.DataFrame, dict]:
    df = base.copy()
    n = len(df)
    kinds = [c for c in COLS for _ in range(PER_COL)]
    rng.shuffle(kinds)
    step = (n - 200) // (len(kinds) + 1)
    truth = {c: {} for c in COLS}
    for j, col in enumerate(kinds):
        i = 100 + step * (j + 1) + rng.randrange(-step // 4, step // 4)
        lo, hi = COLS[col][:2]
        size = round(10 ** rng.uniform(math.log10(lo), math.log10(hi)), 1)
        w = 1 if j % 2 == 0 else 2            # 절반은 두 행 연달아 튐 (시각도 두 행 연달아 깨진 적이 있음: ts_pair)
        for k in range(w):
            df.at[i + k, col] = float(df.at[i + k, col]) + size
        truth[col][i] = (size, w)
    return df, truth


def main() -> None:
    files = sorted((db.ROOT / "data").glob("*.csv.gz"))
    runs = []            # (seed, col, {method: score}, truth{i: size}, unknown set, n)
    unknown_rows = []    # 바탕에서 표시된 행 (정답 모름)
    for f in files:
        base = faults.base_from(f)
        raw = pd.read_csv(f, dtype={"timestamp": str})
        orig_row = np.flatnonzero(~flags(raw).any(axis=1)) + 1     # 바탕 데이터 행 -> 원본 파일 행 번호
        base_flag = {}
        for col in COLS:
            x = base[col].astype(float)
            s_rule, s_h = score_rule(x), score_hampel(x)
            # 바탕의 '정답 모름' 후보: 기준을 많이 낮춘 규칙(지금 기준의 1/10)이나 Hampel 8 이상
            th = COLS[col][2]
            cand = set(np.flatnonzero((s_rule > th / 10) | (s_h > 8)))
            base_flag[col] = {j for i in cand for j in (i - 1, i, i + 1)}   # 바로 옆 행도 영향받으므로 같이 뺀다
            for i in sorted(cand):
                unknown_rows.append((f.name.split("_")[-1][:-7], col, int(orig_row[i]), x.iloc[max(i - 2, 0):i + 3].round(1).tolist(),
                                     float(s_rule[i]), float(s_h[i])))
        for seed in TUNE + TEST:
            df, truth = inject_spikes(base, random.Random(seed))
            for col in COLS:
                x = df[col].astype(float)
                scores = {m: np.nan_to_num(fn(x, seed)) for m, fn in METHODS.items()}
                runs.append((seed, col, scores, truth[col], base_flag[col], len(df)))

    def evaluate(col, method, thr, seeds, width=None):
        """width=None 이면 전체, 1·2 이면 그 폭의 튐만. 튐 안의 행 하나라도 표시하면 잡은 것."""
        hit = {b[0]: [0, 0] for b in BUCKETS}
        fp = rows = 0
        for seed, c, scores, truth, unknown, n in runs:
            if c != col or seed not in seeds:
                continue
            flagged = set(np.flatnonzero(scores[method] > thr))
            rows += n
            spike_rows = {i + k for i, (_, w) in truth.items() for k in range(w)}
            fp += len(flagged - spike_rows - unknown)
            th = COLS[col][2]
            for i, (size, w) in truth.items():
                if width is not None and w != width:
                    continue
                for name, lo, hi in BUCKETS:
                    if lo * th <= size < hi * th:
                        hit[name][1] += 1
                        hit[name][0] += any(i + k in flagged for k in range(w))
        return hit, fp, rows

    lines = ["# 튄 값 탐지: 규칙 vs 통계 필터 vs 모델\n",
             f"`python eval_models.py` · 분석용 3세션, 세션마다 시드 6개 x 열마다 튐 {PER_COL}개. "
             f"기준값은 시드 {TUNE}(조정용)에서 정하고 시드 {TEST}(시험용)에서 잼. 허용 오탐 = 1만 행당 {BUDGET:g}개 이하.\n",
             "크기 = 원래 값에 더한 양, 기준 = 지금 규칙의 앞뒤 차이 기준. 표의 숫자는 시험용 시드 결과.\n"]
    result = {}
    for col, (_, _, th, _) in COLS.items():
        result[col] = {}
        lines += [f"## {col} (지금 기준 {th})\n",
                  "| 방법 | 튐 폭 | 정한 기준값 | " + " | ".join(b[0] for b in BUCKETS) + " | 오탐 (1만 행당) |",
                  "|--|--|--|" + "--|" * (len(BUCKETS) + 1)]
        def row(name, m, thr):
            out = []
            for w in (1, 2):
                hit, fp, rows = evaluate(col, m, thr, TEST, width=w)
                result[col].setdefault(name, {"threshold": float(thr), "fp": fp, "rows": rows})[f"width{w}"] = hit
                out.append(f"| {name} | {w}행 | {thr:.3g} | " + " | ".join(f"{hit[b[0]][0]}/{hit[b[0]][1]}" for b in BUCKETS)
                           + f" | {fp} ({1e4 * fp / rows:.2f}) |")
            return out
        lines += row("지금 규칙", "기준 낮춘 규칙", th)
        for m in METHODS:
            pool = np.concatenate([s[m] for sd, c, s, *_ in runs if c == col and sd in TUNE])
            pos = pool[pool > 0]
            cands = np.geomspace(max(pos.min(), 1e-3), pos.max(), 500)   # 촘촘한 로그 간격 (분위수 간격은 튐 크기 사이를 건너뜀)
            best = None
            for thr in sorted(cands):                       # 낮은 기준부터: 허용 오탐 안에서 가장 낮은 기준
                _, fp_t, rows_t = evaluate(col, m, thr, TUNE)
                if 1e4 * fp_t / rows_t <= BUDGET:
                    best = thr
                    break
            lines += row(m, m, best)
        lines.append("")
    lines += ["## 바탕 데이터에 원래 있던 '정답 모름' 후보\n",
              "결함을 심기 전에 이미 표시된 행. 채점에서 뺐다. 사람이 보고 판단해야 하는 것 (아래 '판단'은 모양만 보고 붙인 추정).\n",
              "| 세션 | 열 | 원본 행 | 앞뒤 2행 포함 값 | 규칙 점수 | Hampel 점수 | 판단 (추정) |", "|--|--|--|--|--|--|--|"]
    for sess, col, i, vals, sr, sh in unknown_rows:
        mid = vals[2] if len(vals) >= 3 else None
        single = len(vals) == 5 and abs(vals[1] - vals[3]) < 0.5 * min(abs(mid - vals[1]), abs(mid - vals[3])) and sr > 0
        lines.append(f"| {sess} | {col} | {i} | {vals} | {sr:.1f} | {sh:.1f} | "
                     f"{'한 행만 튐 → 깨진 값 가능성' if single else '여러 행에 걸친 변화 → 정상 변화일 수 있음'} |")
    (db.ROOT / "eval" / "models_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    (db.ROOT / "eval" / "models_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
