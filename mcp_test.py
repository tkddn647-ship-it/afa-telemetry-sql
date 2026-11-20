"""MCP 서버를 실제로 띄우고 공식 Python SDK 클라이언트로 도구를 불러 결과를 확인한다.

확인 항목:
1. 세션 목록의 행 수 합 = DB의 sample 행 수
2. run_select 로 구한 오후1·2·6차 전류 비율 중앙값 = 0.801 · 0.795 · 0.796 (verify.py 로 검증된 값)
3. 쓰기 문장(DELETE, DROP, 두 문장)은 거절되고 DB 행 수가 그대로
4. 없는 세션 이름이면 오류 응답
"""
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import db

MEDIAN_SQL = (Path(__file__).parent / "sql" / "02_ratio_median.sql").read_text(encoding="utf-8")
MEDIAN_SQL = "\n".join(l for l in MEDIAN_SQL.splitlines() if not l.strip().startswith("--")).strip().rstrip(";")


async def call(s, name, args=None):
    return json.loads((await s.call_tool(name, args or {})).content[0].text)


async def main():
    before = db.connect_readonly().execute("SELECT COUNT(*) FROM sample").fetchone()[0]
    params = StdioServerParameters(command=sys.executable, args=["mcp_server.py"])
    ok = True
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            print("도구:", [t.name for t in (await s.list_tools()).tools])

            sessions = await call(s, "list_sessions")
            total = sum(x["rows"] for x in sessions["sessions"])
            print(f"1. 세션 행 수 합 {total} / DB {before} ->", "일치" if total == before else "불일치")
            ok &= total == before

            med = await call(s, "run_select", {"sql": MEDIAN_SQL})
            got = {row[0]: row[2] for row in med["rows"]}
            want = {"오후1차": 0.801, "오후2차": 0.795, "오후6차": 0.796}
            m_ok = all(got.get(k) == v for k, v in want.items())
            print("2. 비율 중앙값", {k: got.get(k) for k in want}, "->", "일치" if m_ok else "불일치")
            ok &= m_ok

            bad = ["DELETE FROM sample", "DROP TABLE sample", "SELECT 1; DELETE FROM sample",
                   "WITH x AS (SELECT 1) DELETE FROM sample"]
            rejected = [("error" in await call(s, "run_select", {"sql": q})) for q in bad]
            after = db.connect_readonly().execute("SELECT COUNT(*) FROM sample").fetchone()[0]
            print(f"3. 쓰기 시도 {len(bad)}개 중 거절 {sum(rejected)}개, 행 수 {before} -> {after}")
            ok &= all(rejected) and after == before

            q = await call(s, "session_quality", {"label": "오후7차"})
            print("   오후7차 경고:", q.get("warnings"))
            missing = await call(s, "session_quality", {"label": "없는세션"})
            print("4. 없는 세션:", missing.get("error"))
            ok &= "error" in missing
    print("결과:", "통과" if ok else "실패")
    sys.exit(0 if ok else 1)


asyncio.run(main())
