"""세션마다 품질 지표를 쌓아 두고, 새 세션이 기준 세션들과 크게 다르면 알린다 (2026-11-21).

왜: 펌웨어를 고친 뒤 '좋아졌는지'를 감이 아니라 숫자로 판정하려고. 지표의 이력에서 변화를 찾는 생각은 Schelter 외 2018.
기준 세션 = log_date 가 rules/history.csv 위 BASELINE_UNTIL 이하인 세션 (수정 전 펌웨어). 판정하는 세션 자신은 기준에서 뺀다.

판정 방법 (rules/history.csv)
  robust : 기준 세션 값의 중앙값 m 과 MAD x 1.4826 = s. 척도 = max(s, floor). |x - m| > 3 x 척도면 알림.
           floor 를 두는 이유: 값이 거의 같은 세션만 있으면 MAD 가 0 에 가까워져(Pearson 외 2016 의 'implosion') 작은 차이도 알림이 됨.
           기준 세션이 3개 미만이면 '기준 부족'.
  range  : 기준 세션 값의 최소~최대 밖으로 floor 이상 벗어나면 알림. 세션마다 값이 두 무리로 갈리는 지표용
           (그 밖 누락 0.3~8.2%: 중앙값·MAD 로는 실제로 덜 빠진 정상 세션도 알림이 났음, eval_history.py).
  poisson: 결합비(깨진 행 / 그 밖 누락) 전용. 기준 세션들을 합친 비율 p0 = 깨진 행 합 / 그 밖 누락 합.
           새 세션의 그 밖 누락이 n 이면 깨진 행 수 k 는 평균 p0 x n 근처여야 한다. P(K <= k) < 0.001 이면 '줄어듦',
           P(K >= k) < 0.001 이면 '늘어남'. n 이 20 미만이면 '판정 불가'. (깨진 행이 정확히 Poisson 이라는 근거는 없음. 근사)
주행 세션 = 부하 구간(인버터 > 25 A) 1,000행 이상.

사용: python history.py              ->  reports/history.md (모든 세션을 나머지 기준 세션과 비교)
      pipeline.py 가 새 세션마다 judge() 를 불러 보고서에 '기준 대비 변화'를 넣는다.
"""
from __future__ import annotations

import csv
import math
import sqlite3
import statistics

import db

BASELINE_UNTIL = "2026-08-11"      # 이 날까지가 수정 전 펌웨어 (UART 줄 손상, VSM 매핑)
RULES = db.ROOT / "rules" / "history.csv"
DRIVE_MIN_LOAD_ROWS = 1000
ALPHA = 0.001
K = 3.0


def rules() -> list[dict]:
    with open(RULES, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def is_drive(m: dict) -> bool:
    return (m.get("부하_행수") or 0) >= DRIVE_MIN_LOAD_ROWS


def poisson_cdf(k: int, lam: float) -> float:
    """P(K <= k), K ~ Poisson(lam)."""
    if lam <= 0:
        return 1.0
    term = math.exp(-lam)
    total = term
    for i in range(1, k + 1):
        term *= lam / i
        total += term
    return min(total, 1.0)


def sessions(con: sqlite3.Connection, metrics: dict) -> list[dict]:
    """시작 시각 순서. 각 항목: label, log_date, start, 지표들."""
    rows = con.execute("""SELECT se.label, se.log_date, MIN(s.ts_utc) FROM session se JOIN sample s USING (session_id)
                          GROUP BY se.session_id ORDER BY se.log_date, MIN(s.ts_utc)""").fetchall()
    return [{"label": l, "log_date": d, "start": t, **metrics.get(l, {})} for l, d, t in rows]


def judge(target: dict, base: list[dict]) -> list[dict]:
    """target 세션을 base 세션들과 비교. 결과 = 지표마다 {metric, value, baseline, verdict, detail}."""
    out = []
    base = [b for b in base if b["label"] != target["label"]]
    for r in rules():
        metric = r["metric"]
        if r["method"] == "poisson":
            n, k = target.get("그밖_누락") or 0, target.get("깨진_행") or 0
            pool = [b for b in base if (b.get("그밖_누락") or 0) >= 20]
            if n < 20:
                out.append({"metric": metric, "value": target.get(metric), "baseline": None, "verdict": "판정 불가",
                            "detail": f"그 밖 누락 {n:g}개 (20개 미만)"})
                continue
            if len(pool) < 3:
                out.append({"metric": metric, "value": target.get(metric), "baseline": None, "verdict": "기준 부족", "detail": ""})
                continue
            p0 = sum(b["깨진_행"] for b in pool) / sum(b["그밖_누락"] for b in pool)
            lam = p0 * n
            lo = poisson_cdf(int(k), lam)
            hi = 1.0 - poisson_cdf(int(k) - 1, lam) if k > 0 else 1.0
            verdict = "줄어듦" if lo < ALPHA else "늘어남" if hi < ALPHA else "같음"
            out.append({"metric": metric, "value": round(k / n, 3), "baseline": round(p0, 3), "verdict": verdict,
                        "detail": f"깨진 행 {int(k)} (기준대로면 약 {lam:.0f}), P(이만큼 적음) = {lo:.1e}, P(이만큼 많음) = {hi:.1e}"})
            continue
        x = target.get(metric)
        if r["applies_to"] == "주행":
            if not is_drive(target):
                continue
            pool = [b for b in base if is_drive(b)]
        else:
            pool = base
        vals = [b[metric] for b in pool if b.get(metric) is not None]
        if x is None:
            continue
        if len(vals) < 3:
            out.append({"metric": metric, "value": x, "baseline": None, "verdict": "기준 부족", "detail": f"기준 {len(vals)}개"})
            continue
        if r["method"] == "range":
            lo_, hi_, fl = min(vals), max(vals), float(r["floor"])
            if lo_ - fl <= x <= hi_ + fl:
                verdict = "같음"
            else:
                verdict = ("나빠짐" if x > hi_ else "좋아짐") if r["higher_is"] == "악화" else ("좋아짐" if x > hi_ else "나빠짐")
            out.append({"metric": metric, "value": x, "baseline": f"{lo_:g}~{hi_:g}", "verdict": verdict,
                        "detail": f"기준 {len(vals)}개 범위 {lo_:g}~{hi_:g}, 하한 {fl:g}"})
            continue
        m = statistics.median(vals)
        s = 1.4826 * statistics.median(abs(v - m) for v in vals)
        scale = max(s, float(r["floor"]))
        z = (x - m) / scale
        if abs(z) <= K:
            verdict = "같음"
        elif r["higher_is"] == "양쪽":
            verdict = "바뀜"
        else:
            verdict = ("나빠짐" if z > 0 else "좋아짐") if r["higher_is"] == "악화" else ("좋아짐" if z > 0 else "나빠짐")
        out.append({"metric": metric, "value": x, "baseline": round(m, 3), "verdict": verdict,
                    "detail": f"기준 {len(vals)}개 중앙값 {m:g}, 척도 {scale:.3g} (MAD {s:.3g}, 하한 {r['floor']}), z = {z:+.1f}"})
    return out


def baseline_sessions(all_sessions: list[dict]) -> list[dict]:
    return [s for s in all_sessions if s["log_date"] <= BASELINE_UNTIL]


def main() -> None:
    import pipeline
    con = db.connect_readonly()
    metrics = pipeline.session_metrics(con, refresh_views=False)
    ss = sessions(con, metrics)
    base = baseline_sessions(ss)
    lines = ["# 품질 지표 이력과 변화 판정\n",
             f"`python history.py` · 기준 = {BASELINE_UNTIL} 까지의 세션 {len(base)}개 (판정하는 세션 자신은 뺌). 규칙: [`rules/history.csv`](../rules/history.csv)\n",
             "## 지표 이력 (시작 시각 순)\n",
             "| 세션 | 날짜 | 시작(UTC) | 주행 | 행 | 주기 누락 % | 그 밖 누락 % | 깨진 행 % | 결합비 | 전류 비율 |",
             "|--|--|--|--|--|--|--|--|--|--|"]
    for s in ss:
        lines.append(f"| {s['label']} | {s['log_date']} | {s['start'][11:19]} | {'예' if is_drive(s) else '아니오'} | {s.get('전체_행')} | "
                     f"{s.get('주기_누락_pct')} | {s.get('그밖_누락_pct')} | {s.get('깨진_비율_pct')} | {s.get('결합비')} | {s.get('비율_중앙값', '-')} |")
    lines += ["", "## 판정 (각 세션을 나머지 기준 세션과 비교)\n", "| 세션 | 지표 | 값 | 기준 | 판정 | 근거 |", "|--|--|--|--|--|--|"]
    n_alert = 0
    for s in ss:
        for j in judge(s, base):
            alert = j["verdict"] not in ("같음", "판정 불가", "기준 부족")
            n_alert += alert
            lines.append(f"| {s['label']} | {j['metric']} | {j['value']} | {j['baseline']} | {'**' + j['verdict'] + '**' if alert else j['verdict']} | {j['detail']} |")
    lines.insert(2, f"알림 {n_alert}개.\n")
    (db.ROOT / "reports" / "history.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
