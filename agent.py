"""분석 에이전트: 세션 하나를 주면 AI가 MCP 도구(읽기 전용)로 스스로 조사하고, 근거 SQL이 붙은 보고서를 낸다.
보고서의 숫자는 코드가 그 SQL을 다시 실행해 맞는지 확인한다 (AI 주장 검증).

사용: python agent.py 오후2차               ->  reports/agent_오후2차.md
      TELEMETRY_DB=다른.db python agent.py 라벨
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import ask
import db

SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "key_metrics": {
            "type": "object",
            "properties": {
                "missing_rate_pct": {"type": "number"},
                "broken_timestamp_rows": {"type": "integer"},
                "mcu_restarts": {"type": "integer"},
                "pack_to_inverter_ratio_median": {"type": "number"},
            },
            "required": ["missing_rate_pct", "broken_timestamp_rows", "mcu_restarts", "pack_to_inverter_ratio_median"],
        },
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "claim": {"type": "string"},
                    "value": {"type": "number"},
                    "sql": {"type": "string"},
                    "first_row": {"type": ["integer", "null"]},
                    "last_row": {"type": ["integer", "null"]},
                },
                "required": ["title", "claim", "value", "sql"],
            },
        },
    },
    "required": ["summary", "key_metrics", "findings"],
}

TASK = """너는 학생 포뮬러 전기차 주행 로그의 품질 분석가다. 세션 '{label}'을 조사해라.
1. describe_schema 로 표 구조와 분석 규칙을 먼저 읽어라.
2. session_quality 와 run_select 로 품질 지표를 확인해라.
3. 품질 지표에 이미 있는 것 말고도, 신호가 같은 값에 멈춘 구간이나 신호끼리 서로 모순되는 구간처럼 지표에 안 잡히는 이상이 있는지 직접 찾아라.
   찾으면 어느 행부터 어느 행까지인지(row_no) 밝혀라.
4. 결과마다 그 숫자를 다시 계산하는 SELECT 한 문장(sql)과 그 SELECT 결과 첫 행 첫 숫자와 같은 값(value)을 붙여라.
   value 는 반드시 그 sql 을 실행했을 때 나오는 값이어야 한다.
추측은 쓰지 말고, 도구로 확인한 것만 써라. summary, title, claim 은 한국어로 써라."""


def run_agent(label: str, db_path: Path = db.DB, timeout: int = 900) -> dict:
    cfg = {"mcpServers": {"afa": {"command": sys.executable, "args": [str(db.ROOT / "mcp_server.py")],
                                  "env": {"TELEMETRY_DB": str(db_path)}}}}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(cfg, fh)
        cfg_path = fh.name
    cmd = ["claude", "-p", TASK.format(label=label), "--output-format", "json",
           "--mcp-config", cfg_path, "--strict-mcp-config",
           "--allowedTools", "mcp__afa__list_sessions,mcp__afa__describe_schema,mcp__afa__run_select,mcp__afa__session_quality",
           "--disallowedTools", "Bash,Edit,Write,Read,Glob,Grep,WebFetch,WebSearch,Agent",
           "--json-schema", json.dumps(SCHEMA, ensure_ascii=False)]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    os.unlink(cfg_path)
    meta = json.loads(out.stdout)
    rep = meta.get("structured_output")
    if rep is None:
        text = meta.get("result", "")
        rep = json.loads(text[text.find("{"):text.rfind("}") + 1])
    rep["_turns"] = meta.get("num_turns")
    rep["_seconds"] = round(meta.get("duration_ms", 0) / 1000)
    return rep


def first_number(rows):
    for r in rows[:1]:
        for v in r:
            if isinstance(v, (int, float)):
                return v
    return None


def verify(rep: dict, db_path: Path = db.DB) -> list[dict]:
    """AI 주장마다 SQL을 다시 실행해 value 와 같은지 본다."""
    con = db.connect_readonly(db_path)
    out = []
    for f in rep["findings"]:
        try:
            got = first_number(ask.execute(con, ask.guard(f["sql"]))[1])
            ok = got is not None and math.isclose(got, f["value"], rel_tol=1e-2, abs_tol=1e-3)
            out.append({**f, "recomputed": got, "verdict": "재현됨" if ok else "불일치"})
        except Exception as e:
            out.append({**f, "recomputed": None, "verdict": f"실행 불가: {str(e)[:60]}"})
    return out


def write_report(label: str, rep: dict, checked: list[dict], path: Path) -> None:
    ok = sum(c["verdict"] == "재현됨" for c in checked)
    lines = [f"# 분석 에이전트 보고서: {label}\n",
             f"AI가 도구를 {rep.get('_turns')}번 오가며 {rep.get('_seconds')}초 동안 조사. 주장 {len(checked)}개 중 SQL 재실행으로 **{ok}개 재현됨**.\n",
             f"## 요약\n\n{rep['summary']}\n", "## 핵심 지표 (AI가 낸 값)\n",
             *(f"- {k}: {v}" for k, v in rep["key_metrics"].items()), "", "## 발견\n",
             "| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |", "|--|--|--|--|--|--|"]
    for i, c in enumerate(checked, start=1):
        rng = f"{c.get('first_row')}~{c.get('last_row')}" if c.get("first_row") else ""
        lines.append(f"| {i} | **{c['title']}** {c['claim']} | {c['value']} | {c['recomputed']} | {c['verdict']} | {rng} |")
    lines += ["", "## 근거 SQL\n"] + [f"{i}. `{c['sql']}`" for i, c in enumerate(checked, start=1)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    label = sys.argv[1]
    rep = run_agent(label)
    checked = verify(rep)
    out = db.ROOT / "reports" / f"agent_{label}.md"
    write_report(label, rep, checked, out)
    print(out, f"주장 {len(checked)}개, 재현 {sum(c['verdict'] == '재현됨' for c in checked)}개")


if __name__ == "__main__":
    main()
