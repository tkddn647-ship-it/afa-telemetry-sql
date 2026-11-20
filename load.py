"""DB를 처음부터 새로 만들고 로그를 넣는다. 사용: python load.py data/*.csv.gz
(이미 있는 DB에 새 로그만 더하려면 pipeline.py)"""
import sys
from pathlib import Path

import db

con = db.create()
paths = sorted(Path(p) for p in (sys.argv[1:] or (db.ROOT / "data").glob("*.csv.gz")))
for p in paths:
    sid, n = db.load_file(con, p)
    print(f"{p.name}: {n}행")
print("합계", con.execute("SELECT COUNT(*) FROM sample").fetchone()[0], "행 ->", db.DB.name)
