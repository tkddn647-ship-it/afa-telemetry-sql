"""주행 로그 DB를 Claude(데스크톱·Code)가 직접 조회하게 해 주는 MCP 서버.

읽기만 한다. AI가 보내는 SQL도 ask.py 와 같은 안전장치(읽기 전용 연결, SELECT/WITH 한 문장, 5초, 200행)를 지난다.
사용: python mcp_server.py   (Claude 설정에 등록하는 법은 README)
"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

import ask
import db
import pipeline

mcp = MCPServer("afa-telemetry")


@mcp.tool()
def list_sessions() -> dict:
    """넣어 둔 주행 세션 목록 (세션 번호, 라벨, 파일, 행 수)."""
    con = db.connect_readonly()
    rows = con.execute("SELECT session_id, label, file_name, row_count FROM session ORDER BY session_id").fetchall()
    return {"sessions": [{"session_id": a, "label": b, "file": c, "rows": d} for a, b, c, d in rows]}


@mcp.tool()
def describe_schema() -> dict:
    """표·뷰·열 이름, 신호 정의, 보정 계수, 그리고 이 데이터의 분석 규칙. SQL을 쓰기 전에 먼저 읽는다."""
    con = db.connect_readonly()
    notes = (db.ROOT / "prompts" / "notes_v3.md").read_text(encoding="utf-8")
    return {"schema": ask.schema_text(con), "analysis_rules": notes}


@mcp.tool()
def run_select(sql: str) -> dict:
    """SELECT 또는 WITH 한 문장을 실행한다. 쓰기·스키마 변경·PRAGMA·ATTACH는 거절. 최대 200행, 5초."""
    con = db.connect_readonly()
    try:
        cols, rows = ask.execute(con, ask.guard(sql))
    except ask.Rejected as e:
        return {"error": f"거절: {e}"}
    except Exception as e:
        return {"error": f"실행 오류: {e}"}
    return {"columns": cols, "rows": [list(r) for r in rows], "truncated": len(rows) == ask.MAX_ROWS}


@mcp.tool()
def session_quality(label: str) -> dict:
    """세션 하나의 품질 지표(누락률, 깨진 행, 보정 뒤 위반 비율 등)와 경고 규칙 판정."""
    con = db.connect_readonly()
    metrics = pipeline.session_metrics(con, refresh_views=False)
    if label not in metrics:
        return {"error": f"'{label}' 세션이 없습니다", "sessions": list(metrics)}
    return {"label": label, "metrics": metrics[label], "warnings": pipeline.judge(con, metrics[label])}


if __name__ == "__main__":
    mcp.run()
