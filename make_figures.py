"""포트폴리오용 그림 두 장. 사용: python make_figures.py  ->  figures/*.png"""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

import db

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
try:
    font_manager.fontManager.addfont(FONT)
    plt.rcParams["font.family"] = font_manager.FontProperties(fname=FONT).get_name()
except Exception:
    pass  # 다른 PC에서는 기본 글꼴

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
OUT = db.ROOT / "figures"


def style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def fig_current():
    con = db.connect_readonly()
    rows = con.execute(
        "SELECT inv_dc_current, bms_current FROM sample_flags "
        "WHERE session_id IN (1,2,3) AND inv_dc_current > 25 AND NOT bad_inv AND NOT bad_bms").fetchall()
    slope = con.execute(
        "WITH a AS (SELECT COUNT(*) n, SUM(inv_dc_current) sx, SUM(bms_current) sy, SUM(inv_dc_current*inv_dc_current) sxx, "
        "SUM(inv_dc_current*bms_current) sxy FROM sample_flags WHERE session_id IN (1,2,3) AND inv_dc_current > 25 "
        "AND NOT bad_inv AND NOT bad_bms) SELECT (n*sxy-sx*sy)/(n*sxx-sx*sx), (sy-(n*sxy-sx*sy)/(n*sxx-sx*sx)*sx)/n FROM a").fetchone()
    x, y = zip(*rows)
    fig, ax = plt.subplots(figsize=(7, 5), dpi=200, facecolor=SURFACE)
    style(ax)
    ax.scatter(x, y, s=4, color=BLUE, alpha=0.25, linewidths=0)
    lim = 240
    ax.plot([25, lim], [25, lim], color=INK2, linewidth=2, linestyle=(0, (4, 3)))
    ax.text(140, 168, "물리 기준선: 팩 전류 = 인버터 전류\n(정상이라면 점이 이 선보다 위에 있어야 함)", color=INK2, fontsize=9, ha="right",
            bbox=dict(facecolor=SURFACE, edgecolor="none", pad=2))
    a, b = slope
    ax.plot([25, lim], [a * 25 + b, a * lim + b], color=INK, linewidth=2)
    ax.text(lim - 5, 28, f"검은 선 = 최소제곱 직선\n기울기 {a:.2f}, 절편 {b:.1f} A", color=INK, fontsize=9, ha="right",
            bbox=dict(facecolor=SURFACE, edgecolor="none", pad=2))
    ax.set_xlim(20, lim)
    ax.set_ylim(0, lim)
    ax.set_xlabel("인버터 DC 전류 [A]", color=INK2, fontsize=10)
    ax.set_ylabel("배터리 팩 전류 (원본) [A]", color=INK2, fontsize=10)
    ax.set_title(f"부하 구간 {len(rows):,}개 샘플: 팩 전류가 일정한 배율로 작게 기록됨",
                 color=INK, fontsize=11, loc="left")
    fig.text(0.01, 0.01, "A-FA 2026-08-11 실주행 로그 오후1·2·6차, 깨진 값 제외. 비율 중앙값 0.80 → 보정 계수 1.25",
             color=INK2, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "current_scale_error.png", facecolor=SURFACE)


def fig_ai_accuracy():
    """버전마다 실행한 모든 결과를 점으로, 최소~최대를 선으로 (AI는 실행마다 답이 달라 한 번 값으로 말하지 않는다. Atil 2024)."""
    p = db.ROOT / "eval" / "ai_runs.json"            # python tally_ai_runs.py 가 만듦
    if not p.exists():
        return
    runs = json.loads(p.read_text(encoding="utf-8"))

    def scores(base, qset):
        r = runs.get(base, {"runs": {}, "n": 1})
        return list(r["runs"].values()), r["n"]
    versions = ["v1", "v2", "v3", "v4", "v5", "v6"]
    names = {"v1": "v1\n표 구조만", "v2": "v2\n+ 분석 규칙", "v3": "v3\n+ 보정 단서", "v4": "v4\n+ 누락률 정의",
             "v5": "v5\n+ 값 검사 표시", "v6": "v6\n+ 묻지 않으면\n안 뺌"}
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=200, facecolor=SURFACE)
    style(ax)
    ax.grid(axis="x", visible=False)
    for i, v in enumerate(versions):
        for off, qset, base, color in ((-0.17, "questions", v, BLUE), (0.17, "holdout", f"{v}_holdout", ORANGE)):
            sc, n = scores(base, qset)
            if not sc:
                ax.text(i + off, 4, "안 잼", ha="center", color=INK2, fontsize=8)
                continue
            pct = [100 * x / n for x in sc]
            ax.plot([i + off, i + off], [min(pct), max(pct)], color=color, lw=2, solid_capstyle="round")
            ax.scatter([i + off] * len(pct), pct, s=40, color=color, edgecolor=SURFACE, linewidth=1.5, zorder=3)
            lab = f"{min(sc)}/{n}" if min(sc) == max(sc) else f"{min(sc)}~{max(sc)}/{n}"
            ax.text(i + off, max(pct) + 4, lab, ha="center", color=INK, fontsize=8.5)
    ax.set_xticks(range(len(versions)), [names[v] for v in versions])
    ax.set_ylim(0, 115)
    ax.set_ylabel("AI가 맞힌 비율 [%]", color=INK2, fontsize=10)
    ax.set_title("AI가 짠 SQL의 정답률: 실행마다 점 하나, 선은 최소~최대", color=INK, fontsize=11, loc="left")
    fig.text(0.01, 0.01, "버전마다 3번 실행, 지금 정답·채점 규칙으로 다시 채점 (python tally_ai_runs.py). 점수가 같으면 점이 겹침. v2·v5 따로 둔 문항은 안 잼",
             color=INK2, fontsize=8)
    handles = [plt.Line2D([], [], color=BLUE, marker="o", lw=2), plt.Line2D([], [], color=ORANGE, marker="o", lw=2)]
    ax.legend(handles, ["개발용 17문항 (규칙을 고칠 때 본 문항)", "따로 둔 8문항 (규칙을 고칠 때 보지 않은 문항)"],
              frameon=False, fontsize=8, loc="upper left", labelcolor=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "ai_sql_accuracy.png", facecolor=SURFACE)


def fig_models():
    p = db.ROOT / "eval" / "models_result.json"
    if not p.exists():
        return
    r = json.loads(p.read_text(encoding="utf-8"))
    methods = ["지금 규칙", "기준 낮춘 규칙", "Hampel", "IForest", "규칙 v2 (채택)"]
    names = {"지금 규칙": "규칙 v1 (전)", "규칙 v2 (채택)": "규칙 v2 (채택)"}
    colors = [INK2, BLUE, AQUA, ORANGE, YELLOW]
    buckets = list(next(iter(r.values()))["지금 규칙"]["width1"])
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), dpi=200, facecolor=SURFACE, sharey=True)
    w = 0.16
    for ax, width, title in zip(axes, ("width1", "width2"), ("한 행만 튄 값", "두 행 연달아 튄 값")):
        style(ax)
        ax.grid(axis="x", visible=False)
        for j, (m, c) in enumerate(zip(methods, colors)):
            for i, b in enumerate(buckets):
                hit = sum(r[col][m][width][b][0] for col in r)
                tot = sum(r[col][m][width][b][1] for col in r)
                xpos, pct = i + (j - 2) * (w + 0.01), 100 * hit / tot
                ax.bar(xpos, pct, width=w, color=c, label=names.get(m, m) if (i == 0 and width == "width1") else None)
                if pct < 3:
                    ax.text(xpos, 1.5, "0" if hit == 0 else f"{pct:.0f}", ha="center", color=INK2, fontsize=7)
        ax.set_xticks(range(len(buckets)), [b.replace("기준 ", "기준\n") for b in buckets])
        ax.set_title(title, color=INK, fontsize=10, loc="left")
        ax.set_ylim(0, 105)
    axes[0].set_ylabel("잡은 비율 [%]", color=INK2, fontsize=10)
    fig.legend(frameon=False, fontsize=8, loc="upper right", ncol=5, bbox_to_anchor=(0.99, 0.94), labelcolor=INK2)
    fps = {m: (sum(r[c][m]["fp"] for c in r), sum(r[c][m]["rows"] for c in r)) for m in methods}
    fig.suptitle("튄 값 크기별 탐지율 (가로축 = 튄 크기 / 지금 규칙의 기준)", color=INK, fontsize=11, x=0.01, ha="left")
    fig.text(0.01, 0.01, "결함 주입 시험용 시드, 3개 신호 합산. 1만 행당 오탐: "
             + " · ".join(f"{names.get(m, m)} {1e4 * a / b:.2f}" for m, (a, b) in fps.items()), color=INK2, fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 0.9))
    fig.savefig(OUT / "spike_detection.png", facecolor=SURFACE)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    fig_current()
    fig_ai_accuracy()
    fig_models()
    print("figures/current_scale_error.png, figures/ai_sql_accuracy.png, figures/spike_detection.png")
