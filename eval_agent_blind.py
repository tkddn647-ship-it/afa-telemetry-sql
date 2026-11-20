"""분석 에이전트 blind 시험. 규칙에 없는 이상 3종을 숨겨 넣고, 지시문에 이상의 종류를 알려 줄 때(hint)와 안 알려 줄 때(blind)를 비교한다.

정답을 아는 세션: 분석용 3세션 각각에 faults.inject(시드 10+i) + faults.inject_blind (stuck, v_offset, speed_0 각 300행).
같은 DB 를 두 지시문으로 각각 RUNS 번씩 돌린다 (AI 결과는 실행마다 달라서 한 번 값으로 말하지 않는다. Atil 2024).
채점 (eval_agent.py 와 같은 기준):
  - 이상마다: 발견 중 행 범위가 정답 범위의 절반 이상과 겹치는 것이 있으면 찾은 것
  - 그 밖의 발견: 심은 이상과 겹치지 않는 발견 수 (원래 로그에 있던 이상일 수도 있으므로 '오탐'이라 부르지 않는다)
  - 주장 재현: 발견의 SQL을 다시 실행해 value 와 같은 비율
사용: python eval_agent_blind.py [RUNS]   ->  eval/agent_blind_report.md, eval/agent_blind_raw.json
      python eval_agent_blind.py 3 --seed 20 --modes blind,v2 --kinds stuck,v_offset,speed_0,bms_half --tag r2
        -> eval/agent_blind_r2_report.md (새 시드 = 새 위치. bms_half 는 지시문·도구를 고칠 때 보지 않은 종류)
  지시문: hint (이상 종류 예시 있음) · blind (예시 없음) · v2 (blind + column_profile 도구 + '모든 열 확인, 하나 찾고 멈추지 말 것')
"""
from __future__ import annotations

import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

import agent
import db
import faults
from eval_detection import write_gz

EVAL = db.ROOT / "eval"
WORK = db.ROOT / "faulted" / "agent_blind"
OUT = EVAL / "agent_blind"
ALL_KINDS = {"stuck": "인버터 전류 멈춤", "v_offset": "인버터 전압 -25 V", "speed_0": "모터 회전 중 속도 0", "bms_half": "팩 전류 절반"}
KINDS = dict(ALL_KINDS)


def arg(name: str, default: str) -> str:
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def natural(df: pd.DataFrame, min_len: int = 50) -> dict:
    """원래 로그(주입 전)에 같은 모양이 min_len행 이상 이어진 곳이 몇 번 있는지. '그 밖의 발견'을 해석하려고 센다."""
    drive = df.vehicle_speed_kmh > 20

    def runs(m: pd.Series) -> int:
        g = (m != m.shift()).cumsum()
        return int(sum(1 for _, s in m.groupby(g) if s.iloc[0] and len(s) >= min_len))
    stuck = drive & (df.inv_dc_current > 5) & (df.inv_dc_current.diff() == 0)
    return {"stuck": runs(stuck),
            "v_offset": runs((df.motor_main_contactor == 1) & ((df.inv_voltage - df.bms_voltage).abs() > 15)),
            "speed_0": runs((df.vehicle_speed_kmh == 0) & (df.inv_motor_speed > 500)),
            "bms_half": runs((df.inv_dc_current > 25) & (df.bms_current < 0.5 * 0.8 * df.inv_dc_current))}


def build(seed: int = 10, kinds: tuple[str, ...] = ("stuck", "v_offset", "speed_0"), tag: str = "",
          length: int = 300) -> tuple[Path, dict]:
    work = WORK / tag if tag else WORK
    work.mkdir(parents=True, exist_ok=True)
    dbp = work / "agent_blind.db"
    if dbp.exists():
        dbp.unlink()
    con = db.create(dbp)
    truths = {}
    for i, src in enumerate(sorted((db.ROOT / "data").glob("*.csv.gz")), start=1):
        rng = random.Random(seed + i)
        base = faults.base_from(src)
        df, _ = faults.inject(base, rng)
        df, hidden = faults.inject_blind(df, rng, kinds=kinds, length=length)
        label = f"시험{i}"
        path = work / f"sensor_log_20990102_{label}.csv.gz"
        write_gz(df, path)
        db.load_file(con, path)
        truths[label] = {"hidden": hidden, "natural": natural(base, min(50, length))}
    db.refresh_flags(con)
    for label, t in truths.items():          # 심은 구간이 값 검사에 걸려 '깨진 값'으로 빠지지 않았는지 확인
        sid = con.execute("SELECT session_id FROM session WHERE label = ?", (label,)).fetchone()[0]
        for h in t["hidden"]:
            h["value_flagged_rows"] = con.execute(
                "SELECT COUNT(DISTINCT row_no) FROM value_flag WHERE session_id = ? AND row_no BETWEEN ? AND ? AND column_name = ?",
                (sid, h["first_row"], h["last_row"], h["column"])).fetchone()[0]
    con.close()
    return dbp, truths


def overlap(c: dict, h: dict) -> bool:
    if not (c.get("first_row") and c.get("last_row")):
        return False
    need = (h["last_row"] - h["first_row"] + 1) / 2
    return min(c["last_row"], h["last_row"]) - max(c["first_row"], h["first_row"]) + 1 >= need


def score(checked: list[dict], truth: dict) -> dict:
    found = {h["kind"]: any(overlap(c, h) for c in checked) for h in truth["hidden"]}
    other = [c["title"] for c in checked if c.get("first_row") and not any(overlap(c, h) for h in truth["hidden"])]
    return {"found": found, "other": other, "claims": len(checked),
            "reproduced": sum(c["verdict"] == "재현됨" for c in checked)}


def main() -> None:
    runs = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 3
    tag = arg("--tag", "")
    modes = arg("--modes", "hint,blind").split(",")
    kinds = tuple(arg("--kinds", "stuck,v_offset,speed_0").split(","))
    KINDS.clear()
    KINDS.update({k: ALL_KINDS[k] for k in kinds})
    out_dir = OUT if not tag else EVAL / f"agent_blind_{tag}"
    out_dir.mkdir(parents=True, exist_ok=True)
    length = int(arg("--length", "300"))
    dbp, truths = build(int(arg("--seed", "10")), kinds, tag, length)
    jobs = [(mode, label, k) for mode in modes for label in truths for k in range(1, runs + 1)]
    tasks = {"hint": agent.TASK_HINT, "blind": agent.TASK_BLIND, "v2": agent.TASK_V2}
    extra = {"v2": {"schema": agent.SCHEMA_V2, "tools": ",mcp__afa__column_profile"}}

    def go(job):
        mode, label, k = job
        try:
            rep = agent.run_agent(label, dbp, task=tasks[mode], **extra.get(mode, {}))
        except Exception as e:                      # 한 번 실패해도 나머지는 채점
            return {"mode": mode, "label": label, "run": k, "error": str(e)[:200]}
        checked = agent.verify(rep, dbp)
        agent.write_report(label, rep, checked, out_dir / f"{mode}_{label}_r{k}.md")
        return {"mode": mode, "label": label, "run": k, **score(checked, truths[label]),
                "turns": rep.get("_turns"), "seconds": rep.get("_seconds"), "cost_usd": rep.get("_cost_usd"),
                "checked_columns": len(rep.get("checked_columns", []))}

    with ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(go, jobs))
    sfx = f"_{tag}" if tag else ""
    (EVAL / f"agent_blind{sfx}_raw.json").write_text(json.dumps({"truths": truths, "runs": res}, ensure_ascii=False, indent=1, default=str),
                                              encoding="utf-8")

    lines = ["# 분석 에이전트 blind 시험\n",
             f"`python {' '.join(sys.argv)}` · 세션 3개에 규칙에 없는 이상 {len(KINDS)}종(각 {length}행)을 숨기고, 지시문 {len(modes)}가지로 각 {runs}번 실행.\n",
             "- hint: 지시문 3번에 '신호가 같은 값에 멈춘 구간이나 신호끼리 서로 모순되는 구간처럼' 이 있음 (이전 eval_agent.py 와 같음)",
             "- blind: 그 구절을 뺌 ('지표에 안 잡히는 이상이 있는지 직접 찾아라' 만)",
             "- v2: blind + column_profile 도구(열마다 요약) + '모든 열을 확인하고, 하나 찾았다고 멈추지 말 것' (이상 종류는 알려 주지 않음)\n",
             "## 심은 이상\n", "| 세션 | 종류 | 열 | 행 범위 | 값 검사에 걸린 행 | 원래 로그에 같은 모양(50행 이상) |", "|--|--|--|--|--|--|"]
    for label, t in truths.items():
        for h in t["hidden"]:
            lines.append(f"| {label} | {KINDS[h['kind']]} | {h['column']} | {h['first_row']}~{h['last_row']} | "
                         f"{h['value_flagged_rows']} | {t['natural'][h['kind']]}번 |")
    lines += ["", "## 찾은 비율 (세션 3개 × 실행 수)\n", "| 지시문 | " + " | ".join(KINDS.values()) + " | 합계 | 실행별 합계 (최소~최대) | 그 밖의 발견 | 주장 재현 | 실패한 실행 |",
              "|--|" + "--|" * (len(KINDS) + 6)]
    for mode in modes:
        rs = [r for r in res if r["mode"] == mode and "error" not in r]
        bad = sum(1 for r in res if r["mode"] == mode and "error" in r)
        per = [sum(sum(r["found"].values()) for r in rs if r["run"] == k) for k in range(1, runs + 1)
               if any(r["run"] == k for r in rs)]
        cells = [f"{sum(r['found'][kd] for r in rs)}/{len(rs)}" for kd in KINDS]
        tot = sum(sum(r["found"].values()) for r in rs)
        lines.append(f"| {mode} | " + " | ".join(cells) + f" | {tot}/{len(rs) * len(KINDS)} | "
                     f"{min(per) if per else '-'}~{max(per) if per else '-'} / {len(truths) * len(KINDS)} | "
                     f"{sum(len(r['other']) for r in rs)} | {sum(r['reproduced'] for r in rs)}/{sum(r['claims'] for r in rs)} | {bad} |"
                     + (f" 평균 {sum(r['seconds'] or 0 for r in rs) / max(len(rs), 1):.0f}초, ${sum(r['cost_usd'] or 0 for r in rs) / max(len(rs), 1):.2f}/실행" if rs else ""))
    lines += ["", "## 실행별\n", "| 지시문 | 세션 | 실행 | " + " | ".join(KINDS.values()) + " | 그 밖의 발견 | 재현 | 왕복 | 시간 |",
              "|--|--|--|" + "--|" * (len(KINDS) + 4)]
    for r in res:
        if "error" in r:
            lines.append(f"| {r['mode']} | {r['label']} | {r['run']} | 실행 실패: {r['error'][:80]} |")
            continue
        o = lambda b: "찾음" if b else "-"
        lines.append(f"| {r['mode']} | [{r['label']}]({out_dir.name}/{r['mode']}_{r['label']}_r{r['run']}.md) | {r['run']} | "
                     + " | ".join(o(r["found"][kd]) for kd in KINDS)
                     + f" | {'; '.join(r['other'])[:120] or '-'} | {r['reproduced']}/{r['claims']} | {r['turns']} | {r['seconds']}초 |")
    (EVAL / f"agent_blind{sfx}_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
