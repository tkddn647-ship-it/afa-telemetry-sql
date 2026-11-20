"""새 주행 로그가 들어오면: 넣기 -> 품질 검사 -> 경고 판정 -> 세션 보고서.

사용: python pipeline.py inbox/          (폴더 안의 *.csv.gz 중 처음 보는 파일만 처리)
      python pipeline.py inbox/ --all    (보고서를 전체 세션에 대해 다시 만듦)

같은 파일은 내용 해시로 알아보고 다시 넣지 않는다. 경고 기준은 DB의 quality_rule 표에 있다.
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import db

QUERIES = ["02_ratio_median.sql", "05_broken_rows.sql", "06_sample_loss.sql", "07_physics_check.sql"]


def session_metrics(con: sqlite3.Connection, refresh_views: bool = True) -> dict[str, dict]:
    """세션 라벨 -> {지표 이름: 값}. sql/ 의 분석 쿼리를 그대로 다시 쓴다.
    refresh_views=False 는 읽기 전용 연결용 (뷰는 이미 DB에 있음)."""
    if refresh_views:
        con.executescript((db.ROOT / "sql" / "01_flags.sql").read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for name in QUERIES:
        cur = con.execute((db.ROOT / "sql" / name).read_text(encoding="utf-8"))
        cols = [d[0] for d in cur.description]
        for row in cur.fetchall():
            out.setdefault(row[0], {}).update(dict(zip(cols[1:], row[1:])))
    return out


def judge(con: sqlite3.Connection, metrics: dict) -> list[str]:
    warns = []
    for metric, op, th, msg in con.execute("SELECT metric, op, threshold, message FROM quality_rule"):
        v = metrics.get(metric)
        if v is None:
            continue
        if (op == ">" and v > th) or (op == "<" and v < th):
            warns.append(f"{metric} = {v} ({op} {th:g}) — {msg}")
    return warns


def write_report(out_dir: Path, label: str, info: tuple, m: dict, warns: list[str]) -> None:
    file_name, rows, first_ts, last_ts = info
    lines = [
        f"# 세션 보고서: {label}\n",
        f"- 파일: `{file_name}`",
        f"- 행 수: {rows:,}",
        f"- 기록 시각(UTC): {first_ts} ~ {last_ts}\n",
        "## 경고\n",
        *(f"- ⚠ {w}" for w in warns),
        *([] if warns else ["- 없음"]),
        "\n## 품질 지표\n",
        "| 지표 | 값 |", "|--|--|",
        *(f"| {k} | {v} |" for k, v in m.items()),
        "",
    ]
    (out_dir / f"{label}.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("inbox", type=Path)
    ap.add_argument("--all", action="store_true", help="모든 세션의 보고서를 다시 만든다")
    args = ap.parse_args()

    con = db.connect() if db.DB.exists() else db.create()
    new_labels = []
    for p in sorted(args.inbox.glob("*.csv.gz")):
        sid, n = db.load_file(con, p)
        if sid is None:
            print(f"건너뜀 (이미 넣음): {p.name}")
            continue
        label = con.execute("SELECT label FROM session WHERE session_id = ?", (sid,)).fetchone()[0]
        new_labels.append(label)
        print(f"넣음: {p.name} -> {label}, {n:,}행")

    metrics = session_metrics(con)
    out_dir = db.ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    targets = list(metrics) if args.all else new_labels

    info = {r[0]: r[1:] for r in con.execute(
        """SELECT se.label, se.file_name, se.row_count, MIN(s.ts_utc), MAX(s.ts_utc)
           FROM session se JOIN sample s USING (session_id) GROUP BY se.session_id""")}
    summary = []
    for label in metrics:
        warns = judge(con, metrics[label])
        summary.append((label, info[label][1], metrics[label].get("누락률_pct"),
                        metrics[label].get("깨진_비율_pct"), metrics[label].get("비율_중앙값"), len(warns)))
        if label in targets:
            write_report(out_dir, label, info[label], metrics[label], warns)
            print(f"보고서: reports/{label}.md (경고 {len(warns)}개)")

    idx = ["# 전체 세션\n", "`python pipeline.py`가 만든 파일.\n",
           "| 세션 | 행 수 | 누락률 % | 깨진 행 % | 전류 비율 중앙값 | 경고 |", "|--|--|--|--|--|--|"]
    idx += [f"| [{l}]({l}.md) | {n:,} | {a} | {b} | {c} | {w} |" for l, n, a, b, c, w in summary]
    (out_dir / "index.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    if not new_labels:
        print("새 파일 없음")


if __name__ == "__main__":
    main()
