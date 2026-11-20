#!/usr/bin/env bash
# AI를 부르지 않는 검사 전부. 사용: bash test_all.sh
set -e
cd "$(dirname "$0")"
python3 verify.py        # SQL 결과 = pandas 결과
python3 - <<'PY'
import ask, db, sqlite3
for q in ["DELETE FROM sample", "SELECT 1; DROP TABLE sample", "PRAGMA table_info(sample)", "ATTACH 'x' AS y"]:
    try:
        ask.guard(q); raise SystemExit(f"막지 못함: {q}")
    except ask.Rejected:
        pass
try:
    db.connect_readonly().execute("CREATE TABLE t(x)"); raise SystemExit("읽기 전용이 아님")
except sqlite3.OperationalError:
    pass
print("안전장치 4개 + 읽기 전용 확인")
PY
python3 mcp_test.py      # MCP 서버를 띄워 도구 4개 확인
for v in v1 v2 v3 v4; do python3 eval_ai_sql.py $v --regrade | head -1; done
for v in v1 v3 v4; do python3 eval_ai_sql.py $v --holdout --regrade | head -1; done
python3 trace.py | tail -1         # 요구사항 추적표
python3 replay.py --check | tail -1  # 실시간 판정 = SQL 판정 (다르면 실패)
