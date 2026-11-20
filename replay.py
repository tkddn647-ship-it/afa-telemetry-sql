"""실시간 리플레이: 저장된 로그를 한 행씩 흘려보내며, 들어오는 즉시 품질을 판정하고 경고를 낸다.

주행이 끝난 뒤 DB에서 하던 검사(sql/01_flags.sql, sql/06)를 '받는 중에' 하는 버전이다.
판정 규칙은 SQL과 같고(sql/01_flags.sql 규칙 v2, 값 검사 기준은 rules/value_check.csv),
앞뒤 두 행을 봐야 하므로 판정은 2행(약 20 ms) 늦게 나온다.

사용: python replay.py data/sensor_log_20260811_오후7차.csv.gz            (최대 속도로 재생)
      python replay.py <파일> --realtime                                   (실제 속도 100 Hz로 재생, 화면에 경고)
      python replay.py --check                                             (DB의 SQL 판정과 행 단위로 같은지 전체 세션 확인)

경고 종류:
  - 깨진 시각: 행마다 즉시
  - 값 튐: 검사하는 30열 중 튄 열 이름. 3열 이상이면 '행 손상' (한 줄 전체가 밀리거나 깨짐)
  - MCU 재시작: 즉시
  - 최근 10초 누락률 > 8% : 넘으면 켜고, 7% 아래로 내려가야 끔 (8% 근처에서 깜빡이지 않게)
  - 여러 신호 (sql/10): 프리차지 미달(접촉기가 닫힐 때 인버터 전압 < 팩의 95%), 전류 불일치 10행째, 접촉기 열림 중 전류
  - 신호 멈춤: 주행 중(속도 > 5 km/h) 인버터 전류가 5 A 이상인 같은 값으로 50행(약 0.5초) 넘게 — 분석 에이전트가 실제 로그에서 찾은 이상을 규칙으로 옮긴 것
"""
from __future__ import annotations

import argparse
import csv
import gzip
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import db
from verify import VALUE_CHECK

WINDOW_MS = 10_000
LOSS_LIMIT = 8.0
LOSS_CLEAR = 7.0      # 경고를 끄는 기준. 8% 근처에서 경고가 켜졌다 꺼졌다 반복해서(처음 버전) 1%p 여유를 둠
STUCK_ROWS = 50


def _f(v):
    try:
        return float(v) if v not in ("", None) else None
    except ValueError:
        return None


@dataclass
class Detector:
    """SQL 규칙과 같은 판정을 한 행씩. push(row) 하면 2행 전 행의 판정이 확정되어 나온다."""
    buf: deque = field(default_factory=lambda: deque(maxlen=5))
    last_clean_ms: float | None = None
    last_clean_row: int | None = None
    window: deque = field(default_factory=deque)       # (stm_ms, missed) 최근 10초
    loss_alarm: bool = False
    stuck_val: float | None = None
    stuck_len: int = 0
    stuck_alarm: bool = False
    flagged: dict = field(default_factory=lambda: {"bad_ms": set(), "bad_inv": set(), "bad_bms": set(), "bad_speed": set(),
                                                   "bad_value": set()})
    value_flags: set = field(default_factory=set)      # (row_no, 열) — SQL의 value_flag 표와 비교
    alerts: list = field(default_factory=list)
    missed_total: float = 0
    restarts: int = 0
    # 여러 신호 검사 (sql/10 과 같은 정의, 깨진 행은 뺌)
    prev_mc: int | None = None
    mm_run: int = 0
    mm_last_row: int | None = None
    cross: dict = field(default_factory=lambda: {"closures": 0, "precharge_bad": 0, "mismatch": 0, "open_current": 0})

    def push(self, rec: dict | None) -> None:
        self.buf.append(rec)
        if len(self.buf) >= 3:
            self._judge()

    def flush(self) -> None:
        for _ in range(2):
            self.push(None)

    def _spike(self, col, big, near):
        p, x, n = self.buf[-4] if len(self.buf) >= 4 else None, self.buf[-3], self.buf[-2]
        if not (p and x and n) or None in (p[col], x[col], n[col]):
            return False
        return abs(x[col] - p[col]) > big and abs(x[col] - n[col]) > big and abs(n[col] - p[col]) < near

    def _value_cols(self) -> list[str]:
        """5행(앞뒤 2행씩) 중앙값에서 min_dev 넘게 벗어난 열. 5행이 다 있어야 판정 (SQL과 같음)."""
        if len(self.buf) < 5 or None in self.buf:
            return []
        out = []
        tb, tc, td, te = (r["stm_ms"] for r in list(self.buf)[1:])
        for col, md in VALUE_CHECK.items():
            vals = [r[col] for r in self.buf]
            if None in vals:
                continue
            if abs(vals[2] - sorted(vals)[2]) > md:
                # 그 값이 실제로 나타난 시간 (sql/01a 와 같은 정의). 50 ms 넘게 유지됐으면 정상 프레임
                v, b, d = vals[2], vals[1], vals[3]
                ends = (tc, te) if v == d else (tb, td) if v == b else (tc, td)
                dur = None if None in ends else ends[1] - ends[0]
                if dur is None or dur <= 50 or dur < 0 or dur > 1000:
                    out.append(col)
        return out

    def _bad_ms(self):
        b = list(self.buf)
        x = b[-3]
        p = b[-4] if len(b) >= 4 else None
        p2 = b[-5] if len(b) >= 5 else None
        n, n2 = b[-2], b[-1]
        s = lambda r: None if r is None else r["stm_ms"]
        xs, ps, p2s, ns, n2s = s(x), s(p), s(p2), s(n), s(n2)

        def ok(a, c, lo, hi):
            return None not in (xs, a, c) and abs(xs - a) > 1000 and abs(xs - c) > 1000 and lo <= c - a <= hi
        return ok(ps, ns, 0, 200) or ok(ps, n2s, 0, 300) or ok(p2s, ns, 0, 300)

    def _judge(self):
        x = self.buf[-3]
        if x is None:
            return
        r, t = x["row_no"], x["stm_ms"]
        vcols = self._value_cols()
        flags = {"bad_ms": self._bad_ms(),
                 "bad_inv": self._spike("inv_dc_current", 200, 100) or "inv_dc_current" in vcols,
                 "bad_bms": self._spike("bms_current", 100, 50) or "bms_current" in vcols,
                 "bad_speed": self._spike("vehicle_speed_kmh", 30, 15) or "vehicle_speed_kmh" in vcols,
                 "bad_value": bool(vcols)}
        for k, v in flags.items():
            if v:
                self.flagged[k].add(r)
        self.value_flags.update((r, c) for c in vcols)
        if flags["bad_ms"]:
            self.alerts.append((t, r, "깨진 값: 시각"))
        if vcols or flags["bad_inv"] or flags["bad_bms"] or flags["bad_speed"]:
            names = vcols or [k for k in ("bad_inv", "bad_bms", "bad_speed") if flags[k]]
            tag = " → 행 손상" if len(vcols) >= 3 else ""
            self.alerts.append((t, r, f"깨진 값: {len(names)}열 ({', '.join(names[:4])}{' …' if len(names) > 4 else ''}){tag}"))
        if not any(flags.values()):
            self._cross(x, r, t)
        if flags["bad_ms"]:
            return                              # 시각이 깨진 행은 간격 계산에서 뺀다 (06과 같음)
        if self.last_clean_ms is not None:
            d = t - self.last_clean_ms
            skipped = r - self.last_clean_row - 1
            missed = max(round(d / 10.0) - 1 - skipped, 0) if 15 < d <= 1000 else 0
            if d < 0:
                self.restarts += 1
                self.alerts.append((t, r, f"MCU 재시작 (시계가 {self.last_clean_ms:.0f} → {t:.0f} ms)"))
                self.window.clear()
            self.missed_total += missed
            self.window.append((t, missed))
            while self.window and t - self.window[0][0] > WINDOW_MS:
                self.window.popleft()
            span = t - self.window[0][0] if self.window else 0
            if span >= WINDOW_MS * 0.95:
                got, miss = len(self.window), sum(m for _, m in self.window)
                rate = 100.0 * miss / (got + miss)
                if rate > LOSS_LIMIT and not self.loss_alarm:
                    self.loss_alarm = True
                    self.alerts.append((t, r, f"최근 10초 누락률 {rate:.1f}% > {LOSS_LIMIT:g}%"))
                elif rate < LOSS_CLEAR and self.loss_alarm:
                    self.loss_alarm = False
                    self.alerts.append((t, r, f"누락률 회복 {rate:.1f}%"))
        self.last_clean_ms, self.last_clean_row = t, r
        # 신호 멈춤
        inv, v = x["inv_dc_current"], x["vehicle_speed_kmh"]
        # 0 A 근처는 가속 페달을 뗀 정상 상태라 제외 (처음 버전은 타력 주행을 멈춤으로 오인)
        if inv is not None and v is not None and v > 5 and abs(inv) >= 5 and inv == self.stuck_val:
            self.stuck_len += 1
        else:
            if self.stuck_alarm:
                self.alerts.append((t, r, f"인버터 전류 멈춤 끝 ({self.stuck_len + 1}행 동안 {self.stuck_val} A)"))
            self.stuck_val, self.stuck_len, self.stuck_alarm = inv, 0, False
        if self.stuck_len + 1 >= STUCK_ROWS and not self.stuck_alarm:
            self.stuck_alarm = True
            self.alerts.append((t, r, f"인버터 전류가 {STUCK_ROWS}행째 {inv} A에 멈춤 (주행 중)"))


def _cross_check(self, x, r, t):
    """깨진 행이 아닌 행만 받아 여러 신호 검사 (sql/10 과 같은 정의)."""
    mc, iv, bv, ii, bi = (x.get(k) for k in ("motor_main_contactor", "inv_voltage", "bms_voltage", "inv_dc_current", "bms_current"))
    c = self.cross
    if self.prev_mc == 0 and mc == 1:
        c["closures"] += 1
        ratio = iv / bv if bv else None
        if ratio is None or ratio < 0.95:
            c["precharge_bad"] += 1
            self.alerts.append((t, r, f"프리차지 미달: 접촉기가 닫힐 때 인버터 전압 {iv:g} V = 팩의 {100 * (ratio or 0):.0f}% (기준 95%)"))
    self.prev_mc = mc
    if ii is not None and bi is not None and ii > 25 and bi <= 0.5:
        self.mm_run = self.mm_run + 1 if self.mm_last_row == r - 1 else 1
        self.mm_last_row = r
        if self.mm_run == 10:
            c["mismatch"] += 1
            self.alerts.append((t, r, f"전류 불일치: 인버터 {ii:g} A, 팩 {bi:g} A 가 10행째 (한 CAN 주기 넘음)"))
    if mc == 0 and ii is not None and abs(ii) > 5:
        c["open_current"] += 1
        self.alerts.append((t, r, f"접촉기 열림 신호인데 인버터 전류 {ii:g} A"))


Detector._cross = _cross_check


def rows_of(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", newline="") as fh:
        for i, rec in enumerate(csv.DictReader(fh), start=1):
            low = {k.lower(): v for k, v in rec.items()}
            yield {"row_no": i, "stm_ms": _f(low["stm_ms"]), "motor_main_contactor": _f(low["motor_main_contactor"]),
                   **{c: _f(low[c]) for c in VALUE_CHECK}}


def replay(path: Path, realtime: bool = False, quiet: bool = True) -> Detector:
    det = Detector()
    shown = 0
    start, first_ms = time.monotonic(), None
    for rec in rows_of(path):
        if realtime and rec["stm_ms"] is not None:
            first_ms = first_ms if first_ms is not None else rec["stm_ms"]
            lag = (rec["stm_ms"] - first_ms) / 1000 - (time.monotonic() - start)
            if 0 < lag < 1:
                time.sleep(lag)
        det.push(rec)
        if not quiet:
            for t, r, msg in det.alerts[shown:]:
                print(f"[{r:>6}행] {msg}", flush=True)
            shown = len(det.alerts)
    det.flush()
    return det


def check() -> int:
    """모든 세션에서 리플레이 판정 = DB의 SQL 판정 인지 행 단위로 비교."""
    con = db.connect_readonly()
    bad = 0
    table = ["# 실시간 리플레이\n", "`python replay.py --check`가 만든 파일. 저장된 로그를 한 행씩 흘려 받는 중에 판정한 결과.\n",
             "| 세션 | 길이 | 첫 누락률 경고 | 멈춤 경고 | 깨진 값 경고 (행 손상) | 경고 합계 | SQL 판정과 |", "|--|--|--|--|--|--|--|"]
    for sid, label, fname in con.execute("SELECT session_id, label, file_name FROM session ORDER BY session_id").fetchall():
        path = next((p for d in ("data", "inbox", "synthetic") for p in [db.ROOT / d / fname] if p.exists()), None)
        if path is None:
            continue
        det = replay(path)
        sql = {c: {r for (r,) in con.execute(f"SELECT row_no FROM sample_flags WHERE session_id = ? AND {c}", (sid,))}
               for c in det.flagged}
        sql_vf = set(con.execute("SELECT row_no, column_name FROM value_flag WHERE session_id = ?", (sid,)).fetchall())
        loss = {row[0]: row for row in con.execute(open(db.ROOT / "sql" / "06_sample_loss.sql", encoding="utf-8").read())}[label]
        x10 = con.execute(open(db.ROOT / "sql" / "10_cross_signal.sql", encoding="utf-8").read()).fetchall()
        x10 = {row[0]: row for row in x10}[label]
        sql_cross = {"closures": x10[1], "precharge_bad": x10[3], "mismatch": x10[4], "open_current": x10[6]}
        same = (all(det.flagged[c] == sql[c] for c in sql) and det.value_flags == sql_vf
                and det.missed_total == loss[2] and det.restarts == loss[5] and det.cross == sql_cross)
        if det.cross != sql_cross:
            print("  여러 신호 검사 다름:", det.cross, sql_cross)
        bad += not same
        t0 = next(r["stm_ms"] for r in rows_of(path) if r["stm_ms"] is not None)
        dur = con.execute("SELECT COUNT(*) FROM sample WHERE session_id = ?", (sid,)).fetchone()[0] / 100.0
        first_loss = next((t for t, _, m in det.alerts if m.startswith("최근 10초")), None)
        stuck = sum(m.startswith("인버터 전류가") for _, _, m in det.alerts)
        broken = sum(m.startswith("깨진 값") for _, _, m in det.alerts)
        corrupt = sum(m.endswith("행 손상") for _, _, m in det.alerts)
        table.append(f"| {label} | 약 {dur:.0f}초 | {'-' if first_loss is None else f'{(first_loss - t0) / 1000:.0f}초째'} | {stuck} | {broken} ({corrupt}) | "
                     f"{len(det.alerts)} | {'행 단위 일치' if same else '불일치'} |")
        print(f"{'일치' if same else '불일치'} {label}: 값 튐 {len(det.value_flags)}칸 (SQL {len(sql_vf)}), "
              f"빠진 샘플 {det.missed_total:g} (SQL {loss[2]:g}), 재시작 {det.restarts} (SQL {loss[5]}), 경고 {len(det.alerts)}개")
    table.append("\n길이는 행 수 / 100 (10 ms 기준 대략값). MCU 재시작이 있으면 시계가 다시 시작해 경고 시각은 참고용.")
    (db.ROOT / "reports" / "replay.md").write_text("\n".join(table) + "\n", encoding="utf-8")
    return bad


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", type=Path)
    ap.add_argument("--realtime", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        sys.exit(1 if check() else 0)
    t0 = time.monotonic()
    det = replay(a.path, realtime=a.realtime, quiet=False)
    print(f"\n{a.path.name}: 경고 {len(det.alerts)}개, 처리 {time.monotonic() - t0:.1f}초")


if __name__ == "__main__":
    main()
