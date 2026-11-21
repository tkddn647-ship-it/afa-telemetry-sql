"""새 주행 로그가 들어오면: 넣기 -> 품질 검사 -> 경고 판정 -> 세션 보고서.

사용: python pipeline.py inbox/          (폴더 안의 *.csv.gz, *.csv 중 처음 보는 파일만 처리)
      python pipeline.py inbox/ --all    (보고서를 전체 세션에 대해 다시 만듦)
      python pipeline.py old_logs/ --db old.db --out reports_old   (다른 DB·보고서 폴더로)
로그 형식은 머리줄로 알아본다 (rules/formats.csv). MCU 시각이 없는 형식은 누락·시각 지표가 '해당 없음'.

같은 파일은 내용 해시로 알아보고 다시 넣지 않는다. 경고 기준은 DB의 quality_rule 표에 있다.
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import db

QUERIES = ["02_ratio_median.sql", "05_broken_rows.sql", "06_sample_loss.sql", "07_physics_check.sql", "10_cross_signal.sql",
           "11_loss_structure.sql"]


# 지표마다 필요한 신호. 그 신호가 세션 내내 비었거나 0 이면 지표를 None(해당 없음)으로 둔다 (2026-11-21).
# 예: 2026-07 로그는 인버터·BMS 가 CAN 에 안 물려 전부 0 이라, '전류 불일치 0번'은 '없었다'가 아니라 '잴 수 없었다'.
REQUIRES = {
    "접촉기_닫힘": ["motor_main_contactor"], "닫힐때_전압비_최소": ["motor_main_contactor", "inv_voltage", "bms_voltage"],
    "프리차지_미달": ["motor_main_contactor", "inv_voltage", "bms_voltage"],
    "전류_불일치": ["inv_dc_current", "bms_current"], "불일치_최장_행": ["inv_dc_current", "bms_current"],
    "열림중_전류_행": ["motor_main_contactor", "inv_dc_current"],
    "비율_중앙값": ["inv_dc_current", "bms_current"], "부하_행수": ["inv_dc_current", "bms_current"],
}


def session_metrics(con: sqlite3.Connection, refresh_views: bool = True, session_ids: list[int] | None = None) -> dict[str, dict]:
    """세션 라벨 -> {지표 이름: 값}. sql/ 의 분석 쿼리를 그대로 다시 쓴다.
    refresh_views=False 는 읽기 전용 연결용 (표시는 이미 DB에 있음). session_ids 를 주면 그 세션의 표시만 다시 계산."""
    if refresh_views:
        db.refresh_flags(con, session_ids)
    out: dict[str, dict] = {}
    for name in QUERIES:
        cur = con.execute((db.ROOT / "sql" / name).read_text(encoding="utf-8"))
        cols = [d[0] for d in cur.description]
        for row in cur.fetchall():
            out.setdefault(row[0], {}).update(dict(zip(cols[1:], row[1:])))
    silent = db.silent_columns(con)
    for label, m in out.items():
        quiet = set(silent.get(label, []))
        for metric, need in REQUIRES.items():
            if metric in m and quiet & set(need):
                m[metric] = None
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


def write_report(out_dir: Path, label: str, info: tuple, m: dict, warns: list[str], changes: list[dict] | None = None,
                 silent: list[str] | None = None) -> None:
    file_name, rows, first_ts, last_ts, fmt, has_clock = info
    lines = [
        f"# 세션 보고서: {label}\n",
        f"- 파일: `{file_name}`",
        f"- 형식: `{fmt}`" + ("" if has_clock else " (MCU 시각 없음 → 누락·시각·재시작 지표는 해당 없음)"),
        f"- 값 검사 기준: `{db.value_check_files()[db.value_check_format(fmt)].name}`"
        + ("" if db.value_check_format(fmt) == fmt else " (이 형식 전용 기준이 없어 8월 로그 기준을 씀 → 크기가 다른 신호는 덜 잡힐 수 있음)"),
        f"- 행 수: {rows:,}",
        f"- 기록 시각: {first_ts} ~ {last_ts}",
        f"- 기록 안 된 신호 (세션 내내 비었거나 0): {', '.join(silent) if silent else '없음'}\n",
        "## 경고\n",
        *(f"- ⚠ {w}" for w in warns),
        *([] if warns else ["- 없음"]),
        "\n## 기준 세션 대비 변화 (history.py)\n",
        *(f"- {'**' + c['verdict'] + '**' if c['verdict'] not in ('같음', '판정 불가', '기준 부족', '해당 없음') else c['verdict']} "
          f"{c['metric']} = {c['value']} (기준 {c['baseline']}) — {c['detail']}" for c in (changes or [])),
        *([] if changes else ["- 비교 안 함"]),
        "\n## 품질 지표\n",
        "| 지표 | 값 |", "|--|--|",
        *(f"| {k} | {'해당 없음' if v is None else v} |" for k, v in m.items()),
        "",
    ]
    (out_dir / f"{label}.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("inbox", type=Path)
    ap.add_argument("--all", action="store_true", help="모든 세션의 보고서를 다시 만든다")
    ap.add_argument("--db", type=Path, default=db.DB, help="DB 파일 (기본 telemetry.db)")
    ap.add_argument("--out", type=Path, default=db.ROOT / "reports", help="보고서 폴더 (기본 reports/)")
    args = ap.parse_args()

    con = db.connect(args.db) if args.db.exists() else db.create(args.db)
    db.migrate(con)
    had_flags = con.execute("SELECT 1 FROM sqlite_master WHERE name = 'value_flag'").fetchone() is not None
    new_labels, new_ids = [], []
    for p in sorted([*args.inbox.glob("*.csv.gz"), *args.inbox.glob("*.csv")]):
        sid, n = db.load_file(con, p)
        if sid is None:
            print(f"건너뜀 (이미 넣음): {p.name}")
            continue
        label = con.execute("SELECT label FROM session WHERE session_id = ?", (sid,)).fetchone()[0]
        new_labels.append(label)
        new_ids.append(sid)
        print(f"넣음: {p.name} -> {label}, {n:,}행")

    # 튄 값 검사는 새로 넣은 세션만 계산 (전체 다시 하면 약 15초). 예전 DB라 표가 없으면 전체.
    metrics = session_metrics(con, session_ids=new_ids if had_flags else None)
    out_dir = args.out
    out_dir.mkdir(exist_ok=True)
    targets = list(metrics) if args.all else new_labels

    info = {r[0]: r[1:] for r in con.execute(
        """SELECT se.label, se.file_name, se.row_count, MIN(s.ts_utc), MAX(s.ts_utc), se.format, se.has_clock
           FROM session se JOIN sample s USING (session_id) GROUP BY se.session_id""")}
    silent = db.silent_columns(con)
    import history
    hist = history.sessions(con, metrics)
    base = history.baseline_sessions(hist)
    summary = []
    for label in metrics:
        warns = judge(con, metrics[label])
        summary.append((label, info[label][1], metrics[label].get("누락률_pct"),
                        metrics[label].get("깨진_비율_pct"), metrics[label].get("비율_중앙값"), len(warns)))
        if label in targets:
            target = next(h for h in hist if h["label"] == label)
            write_report(out_dir, label, info[label], metrics[label], warns, history.judge(target, base), silent.get(label))
            print(f"보고서: {out_dir / label}.md (경고 {len(warns)}개)")

    idx = ["# 전체 세션\n", "`python pipeline.py`가 만든 파일.\n",
           "| 세션 | 행 수 | 누락률 % | 깨진 행 % | 전류 비율 중앙값 | 경고 |", "|--|--|--|--|--|--|"]
    na = lambda v: "해당 없음" if v is None else v
    idx += [f"| [{l}]({l}.md) | {n:,} | {na(a)} | {na(b)} | {na(c)} | {w} |" for l, n, a, b, c, w in summary]
    (out_dir / "index.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    if not new_labels:
        print("새 파일 없음")


if __name__ == "__main__":
    main()
