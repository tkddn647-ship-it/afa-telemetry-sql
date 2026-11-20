"""말로 질문하면 AI가 SQL을 짜고, 안전장치를 통과한 쿼리만 실행해 답한다.

사용: python ask.py "오후2차에서 가장 빨랐던 속도는?"
      python ask.py --notes v1 "..."      (AI에게 주는 분석 규칙 버전, 기본 v3)

AI 호출은 Claude Code CLI(`claude -p`)를 쓴다. 다른 명령을 쓰려면 환경변수 AI_CMD.

사람이 정한 안전장치 (AI가 바꿀 수 없음):
  1. DB를 읽기 전용으로 연다 (mode=ro + PRAGMA query_only).
  2. SELECT / WITH 로 시작하는 한 문장만 받는다. 쓰기·스키마 변경·ATTACH·PRAGMA 단어가 있으면 실행 전에 거절.
  3. 5초가 넘으면 중단, 결과는 최대 200행.
  4. 실행 오류가 나면 오류 문구를 AI에게 돌려주고 한 번만 다시 짜게 한다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sqlite3
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import db

MAX_ROWS = 200
TIMEOUT_S = 5.0
FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|REPLACE|ATTACH|DETACH|PRAGMA|VACUUM|REINDEX|TRUNCATE)\b", re.I)
NOTES_DIR = db.ROOT / "prompts"


class Rejected(Exception):
    pass


def schema_text(con: sqlite3.Connection) -> str:
    parts = []
    for name, kind in con.execute(
            "SELECT name, type FROM sqlite_master WHERE type IN ('table','view') "
            "AND name NOT LIKE 'sqlite_%' ORDER BY type, name"):
        cols = [r[1] for r in con.execute(f"PRAGMA table_info('{name}')")]
        parts.append(f"{kind} {name}({', '.join(cols)})")
    sig = "\n".join(f"- {c}: {m} [{u or '-'}] {b or ''}" for c, m, u, b in con.execute("SELECT * FROM signal_def"))
    corr = "\n".join(f"- {c} x {f}: {r}" for c, f, r, _ in con.execute("SELECT * FROM scale_correction"))
    sessions = ", ".join(f"{i}={l}" for i, l in con.execute("SELECT session_id, label FROM session ORDER BY 1"))
    return f"{chr(10).join(parts)}\n\n신호 정의:\n{sig}\n\n보정 계수:\n{corr}\n\n세션: {sessions}"


def build_prompt(question: str, schema: str, notes: str, error: str | None = None, prev: str | None = None) -> str:
    p = (
        "너는 SQLite 분석가다. 아래 데이터베이스에서 질문에 답하는 SQLite 쿼리 한 문장만 ```sql 코드 블록으로 써라. "
        "설명은 쓰지 마라. 읽기만 하는 SELECT 또는 WITH 문이어야 한다.\n\n"
        f"[데이터베이스]\n{schema}\n"
    )
    if notes:
        p += f"\n[분석 규칙]\n{notes}\n"
    p += f"\n[질문]\n{question}\n"
    if error:
        p += f"\n[이전 쿼리]\n{prev}\n\n[실행 오류]\n{error}\n이 오류를 고친 쿼리를 다시 써라.\n"
    return p


def call_ai(prompt: str) -> str:
    cmd = shlex.split(os.environ.get("AI_CMD", "claude -p --output-format json"))
    cmd += [prompt, "--disallowedTools", "Bash,Edit,Write,Read,Glob,Grep,WebFetch,WebSearch,Agent"]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    text = out.stdout
    try:
        text = json.loads(text).get("result", text)
    except json.JSONDecodeError:
        pass
    return text


def extract_sql(text: str) -> str:
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S | re.I)
    return (m.group(1) if m else text).strip().rstrip(";").strip()


def guard(sql: str) -> str:
    body = re.sub(r"--[^\n]*", "", sql).strip()
    if not re.match(r"(?is)^\s*(SELECT|WITH)\b", body):
        raise Rejected("SELECT 또는 WITH 로 시작하지 않음")
    if ";" in body:
        raise Rejected("문장이 두 개 이상")
    hit = FORBIDDEN.search(re.sub(r"'[^']*'", "''", body))
    if hit:
        raise Rejected(f"허용하지 않는 단어: {hit.group(1)}")
    return body


def execute(con: sqlite3.Connection, sql: str) -> tuple[list[str], list[tuple]]:
    start = time.monotonic()
    con.set_progress_handler(lambda: 1 if time.monotonic() - start > TIMEOUT_S else 0, 10_000)
    try:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        return cols, cur.fetchmany(MAX_ROWS)
    finally:
        con.set_progress_handler(None, 0)


@dataclass
class Answer:
    question: str
    sql: str = ""
    cols: list[str] = field(default_factory=list)
    rows: list[tuple] = field(default_factory=list)
    attempts: int = 0
    rejected: str | None = None
    error: str | None = None


def ask(question: str, notes_version: str = "v3", con: sqlite3.Connection | None = None) -> Answer:
    con = con or db.connect_readonly()
    notes_file = NOTES_DIR / f"notes_{notes_version}.md"
    notes = notes_file.read_text(encoding="utf-8") if notes_file.exists() else ""
    schema = schema_text(con)
    ans = Answer(question)
    error = None
    for attempt in (1, 2):
        ans.attempts = attempt
        ans.sql = extract_sql(call_ai(build_prompt(question, schema, notes, error, ans.sql if error else None)))
        try:
            safe = guard(ans.sql)
        except Rejected as e:
            ans.rejected = str(e)
            return ans
        try:
            ans.cols, ans.rows = execute(con, safe)
            ans.error = None
            return ans
        except sqlite3.Error as e:
            error = ans.error = str(e)
    return ans


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--notes", default="v3")
    a = ask(ap.parse_args().question, ap.parse_args().notes)
    print("SQL:\n" + a.sql + "\n")
    if a.rejected:
        print("거절:", a.rejected)
    elif a.error:
        print("오류:", a.error)
    else:
        print(" | ".join(a.cols))
        for r in a.rows[:30]:
            print(" | ".join(str(v) for v in r))
    print(f"\n(시도 {a.attempts}번)")


if __name__ == "__main__":
    main()
