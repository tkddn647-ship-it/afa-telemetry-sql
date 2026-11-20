"""CI용 검사: 가짜 데이터(synthetic/)로 파이프라인 전체가 돌고, 결과가 기대한 범위인지 확인한다.
원본 로그 없이 누구나 돌릴 수 있다. 사용: bash ci.sh"""
import re
import sqlite3
import sys
from pathlib import Path

import ask
import db

fails = []


def check(name, ok, detail=""):
    print(("통과 " if ok else "실패 ") + name + (f"  ({detail})" if detail else ""))
    if not ok:
        fails.append(name)


con = db.connect_readonly()
ratio = con.execute((db.ROOT / "sql" / "02_ratio_median.sql").read_text(encoding="utf-8")).fetchall()
check("가짜 데이터에 넣은 배율 0.8을 SQL이 찾음", all(abs(r[2] - 0.8) < 0.01 for r in ratio), str([r[2] for r in ratio]))
loss = con.execute((db.ROOT / "sql" / "06_sample_loss.sql").read_text(encoding="utf-8")).fetchall()
check("누락률 약 5%", all(4 <= r[3] <= 6 for r in loss), str([r[3] for r in loss]))

for q in ["DELETE FROM sample", "SELECT 1; DROP TABLE sample", "PRAGMA table_info(sample)", "ATTACH 'x' AS y"]:
    try:
        ask.guard(q)
        check(f"안전장치가 막음: {q}", False)
    except ask.Rejected:
        check(f"안전장치가 막음: {q}", True)
try:
    con.execute("CREATE TABLE t(x)")
    check("읽기 전용 연결", False)
except sqlite3.OperationalError:
    check("읽기 전용 연결", True)

rep = (db.ROOT / "eval" / "detection_report_synthetic.md").read_text(encoding="utf-8")
ts = re.findall(r"\| ts_\w+ \| \d+ \| \d+ \| ([\d.]+)% \|", rep)
check("깨진 시각 탐지율 100%", ts and all(float(x) == 100.0 for x in ts), str(ts))
fp = [int(x) for x in re.findall(r"\| bad_\w+ \| (\d+) \|", rep)]
check("오탐 0", fp and sum(fp) == 0, str(fp))
big = re.findall(r"\| spike_\w+ \(\S+\) \| [^|]+\| [^|]+\| [^|]+\| (\d+)/(\d+) \|", rep)
check("기준의 2배 넘게 튄 값은 전부 잡음", big and all(a == b for a, b in big), str(big))

sys.exit(1 if fails else 0)
