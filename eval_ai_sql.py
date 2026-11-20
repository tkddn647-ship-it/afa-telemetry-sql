"""AI가 짠 SQL을 정답을 아는 질문으로 채점한다.

사용: python eval_ai_sql.py v1              (prompts/notes_v1.md 를 AI에게 줌, 개발용 17문항)
      python eval_ai_sql.py v3 --holdout    (규칙을 쓸 때 보지 않은 8문항)
      python eval_ai_sql.py v1 --regrade    (AI를 다시 부르지 않고 저장한 답을 지금 규칙으로 재채점)
결과: eval/report_<버전>.md, eval/raw_<버전>.json

채점: 정답 쿼리의 결과 열마다, AI 결과에 값이 같은 열이 있으면 맞음.
      (열 이름·순서·세션 이름 표시 방식은 보지 않음. 숫자는 상대 0.2% 또는 절대 0.001까지 같은 걸로 침)
      깨진 값을 뺀 답도 인정한다: 정답 쿼리의 'FROM sample'을 'FROM sample_clean'으로 바꾼 결과와 같아도 맞음.
"""
from __future__ import annotations

import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import ask
import db

EVAL = db.ROOT / "eval"


def column_values(rows, j):
    return sorted((r[j] for r in rows), key=lambda v: (v is None, v if isinstance(v, (int, float)) else 0))


def same(want, got) -> bool:
    """want = 정답 값. 정답이 반올림돼 있으면(예: 9.2) 그 자리의 절반(0.05)까지 같은 걸로 친다."""
    if want is None or got is None:
        return want is got
    if isinstance(want, (int, float)) and isinstance(got, (int, float)):
        tol = 1e-3
        if isinstance(want, float):
            text = repr(want)
            if "e" not in text and "." in text and len(text.split(".")[1]) <= 3:
                tol = max(tol, 0.5 * 10 ** -len(text.split(".")[1]))
        return math.isclose(want, got, rel_tol=2e-3, abs_tol=tol)
    return str(want) == str(got)


def grade(gold_rows, got_rows) -> tuple[bool, str]:
    if len(got_rows) > len(gold_rows):
        # AI가 값이 0인 세션까지 보여 준 경우: 0/NULL이 들어간 행을 빼고 다시 비교
        trimmed = [r for r in got_rows if not any(v == 0 or v is None for v in r)]
        if len(trimmed) == len(gold_rows):
            ok, why = grade(gold_rows, trimmed)
            return ok, ("값이 0인 세션까지 보여 줌 (인정)" if ok else why)
    if not got_rows and gold_rows:
        return False, "결과 없음"
    if len(gold_rows) != len(got_rows):
        return False, f"행 수 다름 (정답 {len(gold_rows)}, AI {len(got_rows)})"
    ncol = len(got_rows[0])
    for j in range(len(gold_rows[0])):
        want = column_values(gold_rows, j)
        if not any(all(same(x, y) for x, y in zip(want, column_values(got_rows, k))) for k in range(ncol)):
            return False, f"정답 {j + 1}번째 열 값과 같은 열이 없음 (정답 예: {want[:3]})"
    return True, ""


def golds(con, item):
    gold = con.execute(item["gold"]).fetchall()
    alt_sql = item["gold"].replace("FROM sample ", "FROM sample_clean ").replace("FROM sample)", "FROM sample_clean)")
    gold_alt = con.execute(alt_sql).fetchall() if alt_sql != item["gold"] else None
    return gold, gold_alt


def score(a, gold, gold_alt) -> tuple[bool, str]:
    if a.rejected:
        return False, f"안전장치가 거절: {a.rejected}"
    if a.error:
        return False, f"실행 오류: {a.error}"
    ok, why = grade(gold, a.rows)
    if not ok and gold_alt is not None and grade(gold_alt, a.rows)[0]:
        ok, why = True, "깨진 값을 빼고 계산 (인정)"
    return ok, why


def run_one(item, version):
    con = db.connect_readonly()
    gold, gold_alt = golds(con, item)
    a = ask.ask(item["q"], version, con)
    ok, why = score(a, gold, gold_alt)
    return {"id": item["id"], "q": item["q"], "ok": ok, "why": why, "attempts": a.attempts,
            "sql": a.sql, "got": [list(r) for r in a.rows[:12]], "gold": [list(r) for r in gold[:12]]}


def regrade(tag, items):
    """AI를 다시 부르지 않고, 저장해 둔 AI 결과를 지금 채점 규칙으로 다시 채점한다."""
    con = db.connect_readonly()
    old = {r["id"]: r for r in json.loads((EVAL / f"raw_{tag}.json").read_text(encoding="utf-8"))}
    res = []
    for it in items:
        r = old[it["id"]]
        a = ask.Answer(it["q"], sql=r["sql"], attempts=r["attempts"])
        try:
            a.rows = ask.execute(con, ask.guard(r["sql"]))[1]
        except ask.Rejected as e:
            a.rejected = str(e)
        except Exception as e:
            a.error = str(e)
        ok, why = score(a, *golds(con, it))
        res.append({**r, "q": it["q"], "ok": ok, "why": why, "got": [list(x) for x in a.rows[:12]],
                    "gold": [list(x) for x in golds(con, it)[0][:12]]})
    return res


def main() -> None:
    version = sys.argv[1] if len(sys.argv) > 1 else "v3"
    qset = "holdout" if "--holdout" in sys.argv else "questions"
    items = json.loads((EVAL / f"{qset}.json").read_text(encoding="utf-8"))
    tag = version + ("_holdout" if qset == "holdout" else "")
    if "--regrade" in sys.argv:
        res = regrade(tag, items)
    else:
        with ThreadPoolExecutor(max_workers=4) as ex:
            res = sorted(ex.map(lambda it: run_one(it, version), items), key=lambda r: r["id"])
    score = sum(r["ok"] for r in res)
    retried = sum(r["attempts"] > 1 for r in res)
    (EVAL / f"raw_{tag}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    lines = [f"# AI SQL 채점: 설명 {version} · {qset}.json\n", f"**{score}/{len(res)} 맞음** · 오류 뒤 다시 짠 질문 {retried}개\n",
             "| # | 질문 | 결과 | 틀린 이유 |", "|--|--|--|--|"]
    lines += [f"| {r['id']} | {r['q']} | {'맞음' if r['ok'] else '틀림'} | {r['why']} |" for r in res]
    lines += ["\n## AI가 쓴 SQL\n"] + [f"### {r['id']}. {r['q']}\n```sql\n{r['sql']}\n```\n" for r in res]
    (EVAL / f"report_{tag}.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"{version}: {score}/{len(res)} 맞음 (다시 짠 질문 {retried}개)")
    for r in res:
        print(f"  {r['id']:>2} {'O' if r['ok'] else 'X'} {r['why']}")


if __name__ == "__main__":
    main()
