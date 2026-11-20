# 분석 에이전트 보고서: 시험3

AI가 도구를 26번 오가며 103초 동안 조사. 주장 7개 중 SQL 재실행으로 **7개 재현됨**.

## 요약

세션 '시험3'(전체 24,061행)의 품질 지표를 분석 규칙 v6대로 SQL로 다시 계산했고, 모두 session_quality 값과 같았다. 누락률은 10.617036294067388%(빠진 샘플 2,858개)로 기준 8%를 넘는다. 깨진 행은 107행(0.445%)으로 기준 0.05%를 넘는다. MCU 재시작은 4번(행 17710, 19248, 19712, 23397), 기록이 멈춘 구간은 1번(행 557)이다. 부하 구간(5,964행)에서 bms_current/inv_dc_current 비율의 중앙값은 0.79585326953748이다. 지표에 안 잡히는 이상도 하나 찾았다. row_no 9982~10287의 306행 동안 inv_dc_current가 149.9 A로 한 번도 바뀌지 않았다. 같은 구간에서 bms_current는 50.2~190.2 A, 차속은 50.357~89.665 km/h로 계속 바뀌었다. 그런데 이 구간에서 bad_inv 표시는 0건이라 깨진 행·전류 불일치 지표가 이 이상을 잡지 못한다. 이 306행은 부하 구간 분석(비율, 위반 비율)에 그대로 들어간다. 위반_보정후_pct(32.6%)는 도구 안의 판정 기준을 SQL로 똑같이 재현하지 못해서 결과 목록에 넣지 않았다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 10.617036294067388
- broken_timestamp_rows: 60
- mcu_restarts: 4
- pack_to_inverter_ratio_median: 0.79585326953748

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률 10.6% (기준 8% 넘음)** bad_ms 행을 빼고 앞 행과의 stm_ms 간격으로 계산하면 빠진 샘플은 2,858개다. 누락률은 2858/(24061+2858)*100 = 10.617036294067388%로 경고 기준 8%를 넘는다. | 10.617036294067388 | 10.617036294067388 | 재현됨 |  |
| 2 | **깨진 행 107행 (0.445%)** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행이 107행이다. 전체 24,061행의 0.445%로 기준 0.05%를 넘는다. | 107 | 107 | 재현됨 |  |
| 3 | **MCU 재시작 4번** stm_ms 간격이 음수인 곳이 4곳(행 17710, 19248, 19712, 23397)이라 MCU가 4번 재시작했다. 1초 넘게 기록이 멈춘 구간도 1곳(행 557, 간격 4659 ms) 있다. | 4 | 4 | 재현됨 | 17710~23397 |
| 4 | **부하 구간 팩/인버터 전류 비율 중앙값 0.796** 부하 구간(inv_dc_current > 25 A, bad_inv·bad_bms 행 뺀 5,964행)에서 보정 전 bms_current/inv_dc_current의 중앙값은 0.79585326953748이다. scale_correction의 1.25배 계수 근거(약 0.80)와 맞는다. | 0.79585326953748 | 0.79585326953748 | 재현됨 |  |
| 5 | **[지표 밖 이상] 인버터 DC 전류가 149.9 A로 306행 동안 멈춤** row_no 9982부터 10287까지 306행 동안 inv_dc_current가 149.9 A로 똑같다. 0이 아닌 값이 이어진 구간 가운데 세션에서 가장 길고, 두 번째로 긴 구간은 39행뿐이다. 바로 앞 행 9981은 311.2 A, 바로 뒤 행 10288은 78.0 A다. | 306 | 306 | 재현됨 | 9982~10287 |
| 6 | **[지표 밖 이상] 같은 구간에서 팩 전류는 140 A 폭으로 바뀜** inv_dc_current가 149.9 A로 멈춘 row_no 9982~10287 구간에서도 bms_current는 50.2~190.2 A로 140 A 폭만큼 바뀌었고, 차속은 50.357~89.665 km/h로 올라갔다. 실제 전류는 바뀌었는데 인버터 전류 신호만 멈춘 것이다. | 140 | 140.0 | 재현됨 | 9982~10287 |
| 7 | **[지표 밖 이상] 멈춘 구간에 bad_inv 표시 0건** row_no 9982~10287 구간에서 sample_flags의 bad_inv 합은 0이다. 그래서 깨진 행 지표와 전류 불일치 지표(최장 13행)가 이 306행을 잡지 못한다. 부하 구간 분석에서도 이 행들(304행이 부하 조건에 해당)은 빠지지 않고 그대로 들어간다. | 0 | 0 | 재현됨 | 9982~10287 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, CAST(stm_ms AS REAL) ms FROM sample_flags WHERE session_id=3 AND bad_ms=0), d AS (SELECT row_no, ms - LAG(ms) OVER (ORDER BY row_no) d, row_no - LAG(row_no) OVER (ORDER BY row_no) - 1 nb FROM g) SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END)*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=3)+SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END)) AS miss_pct, SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) missing, SUM(d<0) restarts, SUM(d>1000) stops FROM d`
2. `SELECT COUNT(*) FROM sample_flags WHERE session_id=3 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
3. `WITH g AS (SELECT row_no, CAST(stm_ms AS REAL) ms FROM sample_flags WHERE session_id=3 AND bad_ms=0), d AS (SELECT row_no, ms - LAG(ms) OVER (ORDER BY row_no) d FROM g) SELECT SUM(d<0) AS restarts, SUM(d>1000) AS stops FROM d`
4. `WITH r AS (SELECT bms_current*1.0/inv_dc_current x FROM sample_flags WHERE session_id=3 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT x, ROW_NUMBER() OVER (ORDER BY x) rn, COUNT(*) OVER () n FROM r) SELECT AVG(x) median, MAX(n) n FROM o WHERE rn IN ((n+1)/2, (n+2)/2)`
5. `WITH l AS (SELECT row_no, inv_dc_current v, CASE WHEN inv_dc_current = LAG(inv_dc_current) OVER (ORDER BY row_no) THEN 0 ELSE 1 END st FROM sample WHERE session_id=3), g AS (SELECT *, SUM(st) OVER (ORDER BY row_no) gi FROM l) SELECT COUNT(*) AS run_rows, MIN(row_no) AS first_row, MAX(row_no) AS last_row, MIN(v) AS stuck_value FROM g GROUP BY gi HAVING MIN(v)<>0 ORDER BY run_rows DESC LIMIT 1`
6. `SELECT MAX(bms_current)-MIN(bms_current) AS bms_current_span, MIN(bms_current), MAX(bms_current), MIN(vehicle_speed_kmh), MAX(vehicle_speed_kmh) FROM sample WHERE session_id=3 AND row_no BETWEEN 9982 AND 10287`
7. `SELECT SUM(bad_inv) FROM sample_flags WHERE session_id=3 AND row_no BETWEEN 9982 AND 10287`
