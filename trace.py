"""요구사항 추적표: 요구사항 -> 시험 -> 결과 -> 판정. 실패한 항목은 결함 목록에 재현 방법과 함께 남긴다.

사용: python trace.py   ->  reports/traceability.md, reports/defects.md
요구사항은 requirements.yaml 에 있고, 각 요구사항의 test 이름이 이 파일의 함수와 연결된다.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import yaml

import ask
import db
import pipeline

ROOT = db.ROOT
NA = None


def _sql(name):
    return "\n".join(l for l in (ROOT / "sql" / name).read_text(encoding="utf-8").splitlines()
                     if not l.strip().startswith("--")).strip().rstrip(";")


# ---- 세션 시험: (값, 통과 여부, 재현 SQL) 을 돌려준다. 해당 없음이면 (None, None, "") ----
def t_load_issue(con, s, m):
    v = con.execute("SELECT COUNT(*) FROM load_issue li JOIN session se USING (session_id) WHERE se.label = ?", (s,)).fetchone()[0]
    return v, v == 0, f"SELECT * FROM load_issue JOIN session USING (session_id) WHERE label = '{s}';"


def t_broken_ts(con, s, m):
    v = round(100.0 * m["시각_깨짐"] / m["전체_행"], 3)
    return f"{v}%", v <= 0.05, f"SELECT row_no, stm_ms FROM sample_flags JOIN session USING (session_id) WHERE label = '{s}' AND bad_ms;"


def t_loss(con, s, m):
    return f"{m['누락률_pct']}%", m["누락률_pct"] <= 8, "sql/06_sample_loss.sql"


def t_restart(con, s, m):
    return f"{m['MCU_재시작']}회", m["MCU_재시작"] == 0, (
        f"WITH c AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) d FROM sample_flags JOIN session USING (session_id) "
        f"WHERE label = '{s}' AND NOT bad_ms) SELECT row_no, d FROM c WHERE d < 0;")


def _median(con, s, expr):
    q = (f"WITH r AS (SELECT {expr} AS v, ROW_NUMBER() OVER (ORDER BY {expr}) rn, COUNT(*) OVER () n "
         f"FROM sample_flags f JOIN session USING (session_id) CROSS JOIN (SELECT factor k FROM scale_correction WHERE column_name='bms_current') "
         f"WHERE label = ? AND inv_dc_current > 25 AND NOT bad_inv AND NOT bad_bms) SELECT AVG(v) FROM r WHERE rn IN ((n+1)/2, (n+2)/2)")
    return con.execute(q, (s,)).fetchone()[0], q.replace("?", f"'{s}'") + ";"


def t_scale_raw(con, s, m):
    v, q = _median(con, s, "bms_current / inv_dc_current")
    return (NA, NA, "") if v is None else (round(v, 3), 0.95 <= v <= 1.05, q)


def t_scale_corr(con, s, m):
    v, q = _median(con, s, "bms_current * k / inv_dc_current")
    return (NA, NA, "") if v is None else (round(v, 3), 0.95 <= v <= 1.05, q)


def t_physics_corr(con, s, m):
    v = m.get("위반_보정후_pct")
    return (NA, NA, "") if v is None else (f"{v}%", v <= 30, "sql/07_physics_check.sql")


def t_range(con, s, m):
    q = ("SELECT row_no, vehicle_speed_kmh, inv_dc_current FROM sample_clean JOIN session USING (session_id) "
         f"WHERE label = '{s}' AND (vehicle_speed_kmh NOT BETWEEN -1 AND 150 OR inv_dc_current NOT BETWEEN -50 AND 400)")
    v = len(con.execute(q).fetchall())
    return f"{v}행", v == 0, q + ";"


# ---- 시스템 시험 ----
def _detect():
    return (ROOT / "eval" / "detection_report.md").read_text(encoding="utf-8")


def t_detect_ts():
    r = [float(x) for x in re.findall(r"\| ts_\w+ \| \d+ \| \d+ \| ([\d.]+)% \|", _detect())]
    return f"{min(r):g}%", min(r) == 100.0, "python eval_detection.py"


def t_detect_big_spike():
    big = re.findall(r"\| spike_\w+ \(\S+\) \| [^|]+\| [^|]+\| [^|]+\| (\d+)/(\d+) \|", _detect())
    a, b = sum(int(x) for x, _ in big), sum(int(y) for _, y in big)
    return f"{a}/{b}", a == b, "python eval_detection.py"


def t_detect_fp():
    fp = sum(int(x) for x in re.findall(r"\| bad_\w+ \| (\d+) \|", _detect()))
    return f"{fp}건", fp == 0, "python eval_detection.py"


def t_ai_guard():
    bad = ["DELETE FROM sample", "SELECT 1; DROP TABLE sample", "PRAGMA table_info(sample)", "ATTACH 'x' AS y"]
    blocked = 0
    for q in bad:
        try:
            ask.guard(q)
        except ask.Rejected:
            blocked += 1
    try:
        db.connect_readonly().execute("CREATE TABLE t(x)")
        ro = False
    except sqlite3.OperationalError:
        ro = True
    return f"{blocked}/{len(bad)} 거절, 읽기 전용 {'예' if ro else '아니오'}", blocked == len(bad) and ro, "python ask.py (guard, connect_readonly)"


def t_ai_holdout():
    import inspect
    import ask
    v = inspect.signature(ask.ask).parameters["notes_version"].default     # 지금 쓰는 정의서 버전
    r = json.loads((ROOT / "eval" / f"raw_{v}_holdout.json").read_text(encoding="utf-8"))
    ok = sum(x["ok"] for x in r)
    return f"{v}: {ok}/{len(r)} ({100 * ok / len(r):.1f}%)", ok / len(r) >= 0.8, f"python eval_ai_sql.py {v} --holdout"


def mark(p):
    return "-" if p is None else ("통과" if p else "**실패**")


def main() -> None:
    reqs = yaml.safe_load((ROOT / "requirements.yaml").read_text(encoding="utf-8"))
    con = db.connect_readonly()
    metrics = pipeline.session_metrics(con, refresh_views=False)
    sessions = list(metrics)
    g = globals()
    lines = ["# 요구사항 추적표\n", "`python trace.py`가 만든 파일. 요구사항 정의는 [`requirements.yaml`](../requirements.yaml).\n",
             "## 세션별 요구사항\n",
             "| 요구사항 | 기준 | " + " | ".join(sessions) + " |", "|--|--|" + "--|" * len(sessions)]
    defects = []
    summary = {"통과": 0, "실패": 0, "해당 없음": 0}
    for r in [x for x in reqs if x["scope"] == "session"]:
        cells = []
        for s in sessions:
            v, p, how = g[r["test"]](con, s, metrics[s])
            summary["해당 없음" if p is None else ("통과" if p else "실패")] += 1
            cells.append("-" if p is None else f"{mark(p)} {v}")
            if p is False:
                defects.append((r, s, v, how))
        lines.append(f"| **{r['id']}** {r['title']} | {r['criterion']} | " + " | ".join(cells) + " |")
    lines += ["", "## 시스템 요구사항\n", "| 요구사항 | 기준 | 결과 | 판정 | 시험 |", "|--|--|--|--|--|"]
    for r in [x for x in reqs if x["scope"] == "system"]:
        v, p, how = g[r["test"]]()
        summary["통과" if p else "실패"] += 1
        lines.append(f"| **{r['id']}** {r['title']} | {r['criterion']} | {v} | {mark(p)} | `{how}` |")
        if not p:
            defects.append((r, "시스템", v, how))
    lines.insert(2, f"판정 {sum(summary.values())}칸: 통과 {summary['통과']} · 실패 {summary['실패']} · 해당 없음 {summary['해당 없음']} (부하가 없는 세션)\n")
    (ROOT / "reports" / "traceability.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    known = {"REQ-05": "원인 규명: BMS 전류 CAN 신호의 스케일 계수 누락. 조치: 보정 계수 1.25 (REQ-06에서 확인).",
             "REQ-09": "원인 규명 (2026-11-20): 깨진 시각이 실제 MCU 재시작 바로 앞 행에 오면 '앞뒤 간격 0~200 ms' 조건이 성립하지 않아 놓침 "
                       "(300개 중 1개). 미조치: 재시작을 먼저 찾고 그 경계를 빼고 비교하는 방법 검토 필요.",
             "REQ-11": "원인 규명 (2026-11-20): 값 검사(규칙 v2)를 넣은 뒤 생김. 18건 모두 심은 결함이나 빠진 샘플에서 2행 안 — 깨진 값과 값이 바뀌는 "
                       "지점이 붙어 있으면 5행 중앙값이 밀려 바로 옆 정상 행도 표시됨. v1은 오탐 0이었지만 튄 값을 36%만 잡았다(v2는 99.6%). "
                       "기준 '0건'을 유지할지(예: 1만 행당 1건 이하로 바꿀지)는 팀 결정 필요."}
    d = ["# 결함 목록\n", "`python trace.py`가 요구사항 추적표에서 실패한 칸마다 만든 목록. 재현 SQL을 그대로 실행하면 같은 결과가 나온다.\n"]
    for i, (r, s, v, how) in enumerate(defects, start=1):
        d += [f"## DEF-{i:02d} [{r['id']}] {r['title']} — {s}\n",
              f"- 기대: {r['criterion']}", f"- 관찰: {v}", f"- 근거: {r['basis']}",
              f"- 상태: {known.get(r['id'], '열림 (원인 미확인)')}", f"- 재현:\n\n```sql\n{how}\n```\n"]
    (ROOT / "reports" / "defects.md").write_text("\n".join(d), encoding="utf-8")
    print(f"통과 {summary['통과']} · 실패 {summary['실패']} · 해당 없음 {summary['해당 없음']} · 결함 {len(defects)}건")


if __name__ == "__main__":
    main()
