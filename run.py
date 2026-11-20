"""sql/ 폴더의 쿼리를 순서대로 실행하고 결과를 results.md 로 남긴다.

사용: python load.py  ->  python run.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import db

ROOT = Path(__file__).parent
DB = db.DB
OUT = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else ROOT / "results.md"


def md_table(cols: list[str], rows: list[tuple]) -> str:
    head = "| " + " | ".join(cols) + " |\n|" + "--|" * len(cols) + "\n"
    body = "".join("| " + " | ".join("" if v is None else str(v) for v in r) + " |\n" for r in rows)
    return head + body


def main() -> None:
    con = sqlite3.connect(DB)
    db.refresh_flags(con)          # 01a(값 검사 → value_flag 표) + 01(표시 뷰)
    out = ["# 실행 결과\n", "`python run.py`가 만든 파일. 직접 고치지 않는다.\n"]
    for f in sorted((ROOT / "sql").glob("*.sql")):
        if f.name.startswith(("00_", "01")):
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
    OUT.write_text("".join(out), encoding="utf-8")
    con.close()


if __name__ == "__main__":
    main()
