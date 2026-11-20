"""sql/ 폴더의 쿼리를 순서대로 실행하고 결과를 results.md 로 남긴다.

사용: python load.py  ->  python run.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent
DB = ROOT / "telemetry.db"


def md_table(cols: list[str], rows: list[tuple]) -> str:
    head = "| " + " | ".join(cols) + " |\n|" + "--|" * len(cols) + "\n"
    body = "".join("| " + " | ".join("" if v is None else str(v) for v in r) + " |\n" for r in rows)
    return head + body


def main() -> None:
    con = sqlite3.connect(DB)
    out = ["# 실행 결과\n", "`python run.py`가 만든 파일. 직접 고치지 않는다.\n"]
    for f in sorted((ROOT / "sql").glob("*.sql")):
        if f.name.startswith("00_"):
            continue
        sql = f.read_text(encoding="utf-8")
        if "CREATE VIEW" in sql:
            con.executescript(sql)
            continue
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        title = next((l[3:].strip() for l in sql.splitlines() if l.startswith("--")), f.name)
        out.append(f"\n## {f.name}\n\n{title}\n\n{md_table(cols, rows)}")
        print(f"\n== {f.name}")
        print(" | ".join(cols))
        for r in rows:
            print(" | ".join(str(v) for v in r))
    (ROOT / "results.md").write_text("".join(out), encoding="utf-8")
    con.close()


if __name__ == "__main__":
    main()
