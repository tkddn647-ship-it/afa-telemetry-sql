"""품질 규칙(sql/01_flags.sql, sql/06)이 심어 둔 결함을 얼마나 잡는지 잰다.

사용: python eval_detection.py                 (data/ 의 3세션 x 시드 1~5)
      python eval_detection.py --src synthetic/ (공개용 가짜 데이터로)
결과: eval/detection_report.md

행 단위 결함: 잡은 비율(탐지율)과, 정답이 아닌데 깨졌다고 표시한 행(오탐)을 센다.
빠진 샘플·MCU 재시작: 결함을 심기 전 바탕 데이터와의 차이가 심은 양과 같은지 본다.
"""
from __future__ import annotations

import argparse
import gzip
import io
import random
import tempfile
from collections import defaultdict
from pathlib import Path

import pandas as pd

import db
import faults

FLAG_OF = {"ts_drop": "bad_ms", "ts_insert": "bad_ms", "ts_pair": "bad_ms",
           "spike_inv": "bad_inv", "spike_bms": "bad_bms", "spike_speed": "bad_speed"}
LOSS_SQL = "\n".join(l for l in (db.ROOT / "sql" / "06_sample_loss.sql").read_text(encoding="utf-8").splitlines()
                     if not l.strip().startswith("--")).strip().rstrip(";")


def write_gz(df: pd.DataFrame, path: Path) -> None:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        fh.write(buf.getvalue())


def one_run(src: Path, seed: int) -> dict:
    base = faults.base_from(src)
    bad_df, truth = faults.inject(base, random.Random(seed))
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # 파일 이름의 라벨이 세션 라벨이 되므로 구분되게 붙인다
        write_gz(base, td / "sensor_log_00000000_base.csv.gz")
        write_gz(bad_df, td / "sensor_log_00000000_faulted.csv.gz")
        con = db.create(td / "t.db")
        db.load_file(con, td / "sensor_log_00000000_base.csv.gz")
        db.load_file(con, td / "sensor_log_00000000_faulted.csv.gz")
        db.refresh_flags(con)
        flagged = {c: {r for (r,) in con.execute(f"SELECT row_no FROM sample_flags WHERE session_id = 2 AND {c}")}
                   for c in set(FLAG_OF.values())}
        loss = {row[0]: row for row in con.execute(LOSS_SQL)}
        con.close()
    out = {"caught": defaultdict(int), "total": defaultdict(int), "fp": defaultdict(int), "spikes": []}
    truth_by_flag = defaultdict(set)
    for t in truth["rows"]:
        col = FLAG_OF[t["kind"]]
        truth_by_flag[col].add(t["row_no"])
        out["total"][t["kind"]] += 1
        hit = t["row_no"] in flagged[col]
        out["caught"][t["kind"]] += hit
        if "size" in t:
            out["spikes"].append((t["kind"], t["size"], hit))
    marks = {t["row_no"] for t in truth["rows"]} | set(truth["drop_at"])
    out["fp_far"] = 0
    for col, rows in flagged.items():
        fp_rows = rows - truth_by_flag[col]
        out["fp"][col] = len(fp_rows)
        # 심은 결함(어느 종류든)이나 뺀 행 자리에서 2행 넘게 떨어진 오탐: 결함 옆에 붙어 생긴 오탐과 구분
        out["fp_far"] += sum(all(abs(r - m) > 2 for m in marks) for r in fp_rows)
    out["dropped_true"] = truth["dropped_samples"]
    out["dropped_found"] = loss["faulted"][2] - loss["base"][2]
    out["restart_true"] = truth["restarts"]
    out["restart_found"] = loss["faulted"][5] - loss["base"][5]
    out["rows"] = len(bad_df)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=db.ROOT / "data")
    ap.add_argument("--seeds", type=int, default=5)
    a = ap.parse_args()
    files = sorted(a.src.glob("*.csv.gz"))
    caught, total, fp = defaultdict(int), defaultdict(int), defaultdict(int)
    drop_t = drop_f = rs_t = rs_f = rows = fp_far = 0
    spikes = []
    runs = 0
    for f in files:
        for seed in range(1, a.seeds + 1):
            r = one_run(f, seed)
            runs += 1
            for k, v in r["total"].items():
                total[k] += v
                caught[k] += r["caught"][k]
            for k, v in r["fp"].items():
                fp[k] += v
            drop_t += r["dropped_true"]; drop_f += r["dropped_found"]
            rs_t += r["restart_true"]; rs_f += r["restart_found"]
            rows += r["rows"]
            fp_far += r["fp_far"]
            spikes += r["spikes"]
            print(f"{f.name} seed{seed}: " + ", ".join(f"{k} {r['caught'][k]}/{v}" for k, v in sorted(r["total"].items()))
                  + f" | 오탐 {dict(r['fp'])} | 누락 {r['dropped_found']}/{r['dropped_true']} | 재시작 {r['restart_found']}/{r['restart_true']}")

    lines = [f"# 품질 규칙 탐지 성능 (결함 주입)\n",
             f"`python eval_detection.py --src {a.src.name}` · 로그 {len(files)}개 x 시드 {a.seeds}개 = {runs}회, 검사한 행 {rows:,}개\n",
             "| 결함 | 심은 수 | 잡은 수 | 탐지율 |", "|--|--|--|--|"]
    for k in faults.COUNTS:
        if k in total:
            lines.append(f"| {k} | {total[k]} | {caught[k]} | {100 * caught[k] / total[k]:.1f}% |")
    buckets = [("기준의 0.5배 미만", 0, 0.5), ("0.5~1배", 0.5, 1.0), ("1~2배", 1.0, 2.0), ("2배 이상", 2.0, 1e9)]
    lines += ["", "튄 값의 크기별 탐지율 (크기 = 원래 값에 더한 양, 기준 = 01_flags.sql 의 앞뒤 차이 기준)", "",
              "| 결함 (기준) | " + " | ".join(b[0] for b in buckets) + " |", "|--|" + "--|" * len(buckets)]
    for k, th in faults.THRESHOLD.items():
        cells = []
        for _, lo, hi in buckets:
            sel = [h for kk, sz, h in spikes if kk == k and lo * th <= sz < hi * th]
            cells.append(f"{sum(sel)}/{len(sel)}" if sel else "-")
        lines.append(f"| {k} ({th:g}) | " + " | ".join(cells) + " |")
    lines += ["", "| 표시 열 | 오탐 (정답이 아닌데 깨졌다고 표시한 행) |", "|--|--|"]
    lines += [f"| {k} | {v} |" for k, v in sorted(fp.items())]
    lines += ["", f"- 오탐 중 심은 결함·뺀 행 자리에서 2행 넘게 떨어진 것: {fp_far}개 (나머지는 결함 바로 옆 행이 같이 표시된 것)"]
    lines += ["", f"- 빠진 샘플: 심은 {drop_t}개 / 규칙이 센 증가분 {drop_f:g}개",
              f"- MCU 재시작: 심은 {rs_t}번 / 규칙이 센 증가분 {rs_f}번", ""]
    out = db.ROOT / "eval" / f"detection_report{'' if a.src.name == 'data' else '_' + a.src.name}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
