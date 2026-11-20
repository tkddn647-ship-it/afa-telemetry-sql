"""my_answers.sql 을 answers.sql 과 결과로 비교한다. 사용: python study/check.py"""
import re
import sqlite3
from pathlib import Path

HERE = Path(__file__).parent
DB = HERE.parent / "telemetry.db"


def split(path: Path) -> dict[int, str]:
    parts = re.split(r"^-- Q(\d+)\s*$", path.read_text(encoding="utf-8"), flags=re.M)
    return {int(parts[i]): parts[i + 1].strip() for i in range(1, len(parts), 2)}


def run(con, sql):
    rows = con.execute(sql).fetchall()
    return [tuple(round(v, 6) if isinstance(v, float) else v for v in r) for r in rows]


con = sqlite3.connect(DB)
mine, ans = split(HERE / "my_answers.sql"), split(HERE / "answers.sql")
done = 0
for q in sorted(ans):
    if not mine.get(q):
        print(f"Q{q:<3} (아직 안 품)")
        continue
    try:
        ok = run(con, mine[q]) == run(con, ans[q])
    except sqlite3.Error as e:
        print(f"Q{q:<3} 오류: {e}")
        continue
    done += ok
    print(f"Q{q:<3} {'맞음' if ok else '결과가 다름'}")
print(f"\n{done}/{len(ans)} 맞음")
