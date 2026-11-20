#!/usr/bin/env bash
# 원본 로그 없이 가짜 데이터로 전체를 돌리는 검사. GitHub Actions가 push마다 실행한다.
set -e
cd "$(dirname "$0")"
export TELEMETRY_DB="$PWD/ci_synthetic.db"
python synth.py
python load.py synthetic/*.csv.gz
python run.py --out /tmp/ci_results.md
python eval_detection.py --src synthetic --seeds 2 > /dev/null
python ci_check.py
