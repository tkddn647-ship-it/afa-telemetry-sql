"""분석 에이전트 채점. 정답을 아는 세션을 만들어 놓고 에이전트에게 조사시킨다.

정답을 아는 세션: 분석용 3세션 각각에 faults.inject(시드 11) + 품질 규칙에 없는 '신호 멈춤' 하나(faults.inject_stuck)를 심음.
채점:
  1. 핵심 지표 4개가 규칙 계산값·심은 정답과 같은가 (누락률 ±0.1%p, 깨진 시각 행 수, MCU 재시작 수, 비율 중앙값 ±0.005)
  2. 규칙에 없는 '멈춤'을 찾았나: 발견 중 행 범위가 정답 범위의 절반 이상과 겹치는 것이 있으면 찾은 것
  3. 주장 재현율: 모든 발견의 SQL을 다시 실행해 값이 같은 비율
사용: python eval_agent.py   ->  eval/agent_report.md (에이전트 3번 실행, 각 1~3분)
"""
from __future__ import annotations

import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import agent
import db
import faults
import pipeline
from eval_detection import write_gz

EVAL = db.ROOT / "eval"
WORK = db.ROOT / "faulted" / "agent"


def build() -> tuple[Path, dict]:
    WORK.mkdir(parents=True, exist_ok=True)
    dbp = WORK / "agent_eval.db"
    con = db.create(dbp)
    truths = {}
    for i, src in enumerate(sorted((db.ROOT / "data").glob("*.csv.gz")), start=1):
        rng = random.Random(10 + i)
        df, t = faults.inject(faults.base_from(src), rng)
        df, stuck = faults.inject_stuck(df, rng)
        label = f"시험{i}"
        path = WORK / f"sensor_log_20990101_{label}.csv.gz"
        write_gz(df, path)
        db.load_file(con, path)
        truths[label] = {"restarts": t["restarts"],
                         "broken_ts": sum(r["kind"].startswith("ts_") for r in t["rows"]), "stuck": stuck}
    con.executescript((db.ROOT / "sql" / "01_flags.sql").read_text(encoding="utf-8"))
    m = pipeline.session_metrics(con)
    for label in truths:
        truths[label]["rule"] = m[label]
    con.close()
    return dbp, truths


def score(label, rep, checked, truth) -> dict:
    km, rule = rep["key_metrics"], truth["rule"]
    con = db.connect_readonly(WORK / "agent_eval.db")
    ratio = con.execute((db.ROOT / "sql" / "02_ratio_median.sql").read_text(encoding="utf-8")).fetchall()
    ratio = {r[0]: r[2] for r in ratio}[label]
    metric_ok = {
        "누락률": abs(km["missing_rate_pct"] - rule["누락률_pct"]) <= 0.1,
        "깨진 시각 행": km["broken_timestamp_rows"] == truth["broken_ts"],
        # 정답 = 심은 재시작 + 바탕 로그에 원래 있던 재시작. 규칙의 재시작 탐지는 결함 주입 시험에서 심은 수와 정확히 같았으므로(REQ-09)
        # 규칙 값을 정답으로 쓴다.
        "MCU 재시작": km["mcu_restarts"] == rule["MCU_재시작"],
        "전류 비율": abs(km["pack_to_inverter_ratio_median"] - ratio) <= 0.005,
    }
    s = truth["stuck"]
    need = (s["last_row"] - s["first_row"] + 1) / 2
    found = any(c.get("first_row") and c.get("last_row") and
                min(c["last_row"], s["last_row"]) - max(c["first_row"], s["first_row"]) + 1 >= need for c in checked)
    return {"label": label, "metrics": metric_ok, "stuck_found": found, "stuck": s,
            "claims": len(checked), "reproduced": sum(c["verdict"] == "재현됨" for c in checked),
            "turns": rep.get("_turns"), "seconds": rep.get("_seconds")}


def main() -> None:
    dbp, truths = build()

    def go(label):
        rep = agent.run_agent(label, dbp)
        checked = agent.verify(rep, dbp)
        agent.write_report(label, rep, checked, EVAL / f"agent_{label}.md")
        return score(label, rep, checked, truths[label])

    with ThreadPoolExecutor(max_workers=3) as ex:
        res = list(ex.map(go, truths))
    m_ok = sum(sum(r["metrics"].values()) for r in res)
    m_all = sum(len(r["metrics"]) for r in res)
    lines = ["# 분석 에이전트 채점\n",
             f"정답을 아는 세션 {len(res)}개. 핵심 지표 **{m_ok}/{m_all}** 정확 · 규칙에 없는 멈춤 **{sum(r['stuck_found'] for r in res)}/{len(res)}** 발견 · "
             f"주장 재현 **{sum(r['reproduced'] for r in res)}/{sum(r['claims'] for r in res)}**\n",
             "| 세션 | 누락률 | 깨진 시각 | 재시작 | 전류 비율 | 멈춤 발견 (정답 범위) | 주장 재현 | 도구 왕복 | 시간 |",
             "|--|--|--|--|--|--|--|--|--|"]
    o = lambda b: "맞음" if b else "틀림"
    for r in res:
        mm = r["metrics"]
        lines.append(f"| [{r['label']}](agent_{r['label']}.md) | {o(mm['누락률'])} | {o(mm['깨진 시각 행'])} | {o(mm['MCU 재시작'])} | {o(mm['전류 비율'])} | "
                     f"{'찾음' if r['stuck_found'] else '못 찾음'} ({r['stuck']['column']} {r['stuck']['first_row']}~{r['stuck']['last_row']}) | "
                     f"{r['reproduced']}/{r['claims']} | {r['turns']} | {r['seconds']}초 |")
    (EVAL / "agent_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (EVAL / "agent_raw.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
