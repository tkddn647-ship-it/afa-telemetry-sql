"""AI SQL 채점의 모든 실행(raw_<버전>[_holdout][_runK].json)을 지금 정답·채점 규칙으로 다시 채점해 eval/ai_runs.json 에 저장.
AI 는 실행마다 답이 달라서 점수를 한 번 값이 아니라 최소~최대로 보고한다 (Atil 2024). 그림(make_figures.py)은 이 파일을 읽는다.
사용: python tally_ai_runs.py   (AI 를 부르지 않음. 정답 쿼리 때문에 몇 분 걸림)
"""
from __future__ import annotations

import json

import eval_ai_sql as e

VERSIONS = ["v1", "v2", "v3", "v4", "v5", "v6"]

_gold_cache: dict = {}
_golds = e.golds


def cached_golds(con, item):                 # 정답 쿼리는 실행마다 같으므로 한 번만 계산 (regrade 가 문항마다 2번 부름)
    key = item["gold"]
    if key not in _gold_cache:
        _gold_cache[key] = _golds(con, item)
    return _gold_cache[key]


e.golds = cached_golds


def tags_of(base: str) -> list[str]:
    tags = [p.stem[4:] for p in sorted(e.EVAL.glob(f"raw_{base}*.json"))
            if p.stem[4:] == base or p.stem[4:].startswith(base + "_run")]
    if base + "_run1" in tags:            # raw_<v>.json 이 run1 과 같은 실행의 사본인 경우 (v5, v6)
        tags.remove(base)
    return tags


def main() -> None:
    out = {}
    for qset, suffix in (("questions", ""), ("holdout", "_holdout")):
        items = json.loads((e.EVAL / f"{qset}.json").read_text(encoding="utf-8"))
        for v in VERSIONS:
            base = v + suffix
            runs = {t: sum(r["ok"] for r in e.regrade(t, items)) for t in tags_of(base)}
            out[base] = {"n": len(items), "runs": runs}
            sc = list(runs.values())
            print(base, f"{min(sc)}~{max(sc)}/{len(items)}" if sc else "안 잼", runs)
    (e.EVAL / "ai_runs.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
