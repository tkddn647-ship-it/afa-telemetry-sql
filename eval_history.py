"""변화 판정(history.py) 시험: 실제 세션을 고친 사본이 판정에 어떻게 잡히는지 잰다 (2026-11-21).

사용: python eval_history.py   ->  eval/history_report.md
깨진 행이 있는 주행 세션 6개마다 사본을 만들어 실제 적재 경로(파일 -> DB -> 값 검사 -> sql/)로 지표를 내고,
원래 세션을 뺀 나머지 기준 세션 9개와 비교한다.
  원본         : 그대로. 정답 = 알림 없음
  수정 펌웨어  : 깨진 행을 모두 지움 (손상된 줄이 저장되는 대신 버려졌다고 가정). 정답 = 결합비 '줄어듦'
  부분 수정 f  : 깨진 행 중 f 만 남김 (f = 0.5, 0.25). 정답 = '줄어듦' (얼마나 작은 효과까지 잡는지 보려는 것)
  손상 2배     : 깨진 행 수만큼 정상 행의 인버터 전류를 10배로 (숫자 글자 끼어듦 흉내, 누락은 그대로). 정답 = '늘어남'
  BMS 배율 수정: 팩 전류 x 1.25. 정답 = 전류 비율 '바뀜'
'정답'은 바꾼 방식에서 정해진다. 수정 펌웨어 사본은 '손상된 줄이 버려진다'는 가정이고, 실제 수정 펌웨어 로그는 아직 없다.
"""
from __future__ import annotations

import random
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

import db
import history
import pipeline
from eval_detection import write_gz
from verify import flags

FILES = sorted((db.ROOT / "inbox").glob("*.csv.gz"))


def metrics_of(df: pd.DataFrame, label: str) -> dict:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / f"sensor_log_20990101_{label}.csv.gz"
        write_gz(df, p)
        con = db.create(Path(td) / "t.db")
        db.load_file(con, p)
        m = pipeline.session_metrics(con)
        s = history.sessions(con, m)[0]
        con.close()
    return s


def variants(df: pd.DataFrame, rng: random.Random) -> dict:
    bad = flags(df).any(axis=1).to_numpy()
    idx = np.flatnonzero(bad)
    out = {"원본": df}
    out["수정 펌웨어"] = df[~bad].reset_index(drop=True)
    for f in (0.5, 0.25):
        keep = set(rng.sample(list(idx), int(round(f * len(idx)))))
        out[f"부분 수정 {f}"] = df[[(not b) or (i in keep) for i, b in enumerate(bad)]].reset_index(drop=True)
    d2 = df.copy()
    ok = np.flatnonzero(~bad & (df.inv_dc_current.abs() > 5).to_numpy())
    ok = ok[(ok > 5) & (ok < len(df) - 5)]
    pick = rng.sample(list(ok), min(len(idx), len(ok)))
    d2.loc[pick, "inv_dc_current"] = (d2.loc[pick, "inv_dc_current"] * 10).round(1)
    out["손상 2배"] = d2
    d3 = df.copy()
    d3["bms_current"] = (d3.bms_current * 1.25).round(1)
    out["BMS 배율 수정"] = d3
    return out


WANT = {"원본": ("알림 없음", None), "수정 펌웨어": ("결합비", "줄어듦"), "부분 수정 0.5": ("결합비", "줄어듦"),
        "부분 수정 0.25": ("결합비", "줄어듦"), "손상 2배": ("결합비", "늘어남"), "BMS 배율 수정": ("비율_중앙값", "바뀜")}


NEED: dict = {}


def min_n_up(p0: float, f: float, power: float = 0.9) -> int | None:
    """깨진 행이 f 배로 늘었을 때 '늘어남'이 power 확률로 나오는 그 밖 누락 수."""
    for n in range(10, 20001, 5):
        lam0 = p0 * n
        kc = 0
        while 1 - history.poisson_cdf(kc - 1, lam0) >= history.ALPHA:
            kc += 1
        if 1 - history.poisson_cdf(kc - 1, f * lam0) >= power:
            return n
    return None


def min_n(p0: float, f: float, power: float = 0.9) -> int | None:
    """깨진 행이 기준의 f 배로 줄었을 때, 세션 하나에서 power 확률로 '줄어듦'이 나오려면 그 밖 누락이 몇 개 필요한가 (Poisson 근사)."""
    for n in range(10, 20001, 5):
        lam0 = p0 * n
        kc = -1
        while history.poisson_cdf(kc + 1, lam0) < history.ALPHA:
            kc += 1
        if kc >= 0 and history.poisson_cdf(kc, f * lam0) >= power:
            return n
    return None


def main() -> None:
    con = db.connect_readonly()
    real = history.sessions(con, pipeline.session_metrics(con, refresh_views=False))
    rng = random.Random(7)
    rows, ok_n, all_n, extra, low_power = [], 0, 0, [], []
    allb = [x for x in history.baseline_sessions(real) if (x.get("그밖_누락") or 0) >= 20]
    p0 = sum(x["깨진_행"] for x in allb) / sum(x["그밖_누락"] for x in allb)
    NEED.update({"수정 펌웨어": min_n(p0, 0.0), "부분 수정 0.25": min_n(p0, 0.25), "부분 수정 0.5": min_n(p0, 0.5),
                 "손상 2배": min_n_up(p0, 2.0)})
    for f in FILES:
        label = db.label_of(f)
        r0 = next(s for s in real if s["label"] == label)
        if not history.is_drive(r0) or not r0.get("깨진_행"):
            continue
        base = [s for s in history.baseline_sessions(real) if s["label"] != label]
        df = pd.read_csv(f, dtype={"timestamp": str})
        for name, v in variants(df, rng).items():
            s = metrics_of(v, label)
            js = history.judge(s, base)
            alerts = [j for j in js if j["verdict"] not in ("같음", "판정 불가", "기준 부족")]
            metric, want = WANT[name]
            if want is None:
                good = not alerts
            else:
                good = any(j["metric"] == metric and j["verdict"] == want for j in js)
            other = [f"{j['metric']} {j['verdict']}" for j in alerts if j["metric"] != metric]
            ok_n += good
            all_n += 1
            need = NEED.get(name)
            if need is not None and (s.get("그밖_누락") or 0) < need:
                low_power.append((label, name, good))
            c = next(j for j in js if j["metric"] == "결합비")
            rows.append(f"| {label} | {name} | {s.get('깨진_행')} | {s.get('그밖_누락'):g} | {c['value']} | {c['verdict']} | "
                        f"{', '.join(other) or '-'} | {'O' if good else 'X'} |")
            if other:
                extra.append((label, name, other))
    lines = ["# 변화 판정 시험 (history.py)\n",
             "`python eval_history.py` · 깨진 행이 있는 주행 세션 6개를 고친 사본을 실제 적재 경로로 지표 계산 → 원래 세션을 뺀 기준 9개와 비교.\n",
             f"**맞음 {ok_n}/{all_n}**\n",
             "| 세션 | 사본 | 깨진 행 | 그 밖 누락 | 결합비 | 결합비 판정 | 다른 알림 | 맞음 |", "|--|--|--|--|--|--|--|--|"] + rows
    good_hp = sum(1 for r_ in rows if r_.endswith("O |")) - sum(g for *_, g in low_power)
    lines.insert(3, f"그 밖 누락이 아래 '필요한 수'보다 적은 사본 {len(low_power)}개를 빼면 **{good_hp}/{all_n - len(low_power)}** "
                    f"(빠진 것: {', '.join(f'{a} {b}' for a, b, _ in low_power) or '없음'})\n")
    lines += ["", f"## 세션 하나로 판정하려면 (기준 결합비 p0 = {p0:.3f}, 유의수준 0.001, 90% 확률)\n",
              "| 수정 뒤 남은 손상 | 필요한 그 밖 누락 | 대략 (누락 1% 세션이면) |", "|--|--|--|"]
    for f in (0.0, 0.25, 0.5):
        n = min_n(p0, f)
        lines.append(f"| {int(f * 100)}% | {n}개 | 약 {n / 0.01 / 100 / 60:.1f}분 주행 (100 Hz) |" if n else f"| {int(f * 100)}% | 2만 개 넘음 | - |")
    n2 = min_n_up(p0, 2.0)
    lines.append(f"| 200% (손상 2배) | {n2}개 | 약 {n2 / 0.01 / 100 / 60:.1f}분 주행 (100 Hz) |")
    lines += ["", "정답: 원본 = 알림 없음, 수정·부분 수정 = 결합비 줄어듦, 손상 2배 = 결합비 늘어남, BMS 배율 수정 = 전류 비율 바뀜. "
              "'다른 알림'은 정답 지표가 아닌 곳에서 난 알림 (예: 깨진 행을 지우면 깨진 행 비율도 좋아짐 — 틀린 알림은 아님)."]
    (db.ROOT / "eval" / "history_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
