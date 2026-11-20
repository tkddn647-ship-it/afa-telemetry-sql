# 분석 에이전트 보고서: 시험3

AI가 도구를 22번 오가며 92초 동안 조사. 주장 6개 중 SQL 재실행으로 **6개 재현됨**.

## 요약

세션 '시험3'(전체 24,061행)을 분석 규칙 v6에 따라 SQL로 다시 계산해 보니 session_quality 지표와 같았다. 누락률 10.617036294067388%로 8% 기준을 넘었고, MCU 재시작 4번(row 17710, 19248, 19712, 23397), 기록이 끊긴 구간 1번(row 556→557, 4,659 ms)이 있었다. 깨진 행은 107행(0.44470304642367314%)이고, 부하 구간의 bms_current/inv_dc_current 비율 중앙값은 0.79585326953748이다. 지표에 안 잡히는 이상으로는 row 5786~6085(300행)에서 vehicle_speed_kmh가 계속 0인데 inv_motor_speed는 1115~2900 rpm이고 그중 228행이 부하 구간(inv_dc_current>25 A)인 모순을 찾았다. 이 구간 밖에서는 모터 회전수가 500 rpm을 넘는 12,367행 모두 차량 속도가 0보다 크다. 그래서 이 구간은 속도 신호가 0에 멈춘 이상으로 본다. 조향각이 -49.7에 멈춘 구간(row 18258~19247)은 차량이 서 있던 때(모터 회전수 최대 54 rpm)라서 이상으로 보지 않았다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 10.617036294067388
- broken_timestamp_rows: 60
- mcu_restarts: 4
- pack_to_inverter_ratio_median: 0.79585326953748

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률 8% 넘음** bad_ms 행을 빼고 stm_ms 간격으로 계산하면 빠진 샘플이 2,858개이고, 누락률은 10.617036294067388%로 경고 기준 8%를 넘는다. | 10.617036294067388 | 10.617036294067388 | 재현됨 |  |
| 2 | **주행 중 MCU 재시작 4번** stm_ms가 거꾸로 간 곳이 4군데다. row 17710, 19248, 19712, 23397에서 MCU가 재시작했다. | 4 | 4 | 재현됨 | 17710~23397 |
| 3 | **기록이 끊긴 구간 1번** row 556과 557 사이 stm_ms 간격이 4,659 ms다. 1,000 ms를 넘으므로 기록이 끊긴(멈춘) 구간 1번이다. | 4659 | 4659 | 재현됨 | 556~557 |
| 4 | **깨진 행 107행 (0.4447%)** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행이 107행이다(시각 깨짐 60행 포함). 세션 전체 대비 0.44470304642367314%로 기준 0.05%를 넘는다. | 107 | 107 | 재현됨 |  |
| 5 | **부하 구간 팩/인버터 전류비 중앙값 약 0.796** 부하 구간(inv_dc_current>25 A, bad_inv·bad_bms 행 제외, 5,964행)에서 보정 전 bms_current/inv_dc_current 비율의 중앙값은 0.79585326953748이다. | 0.79585326953748 | 0.79585326953748 | 재현됨 |  |
| 6 | **차량 속도 0인데 모터가 도는 모순 구간 (지표 밖 이상)** row 5786~6085의 300행 동안 vehicle_speed_kmh가 계속 0.0이다. 그런데 inv_motor_speed는 1115~2900 rpm(평균 2186.36)이고, 300행 중 228행은 inv_dc_current>25 A인 부하 구간이다. 바로 앞 row 5785는 36.239 km/h, 바로 뒤 row 6086은 24.79 km/h다. 이 구간 밖에서는 모터 회전수가 500 rpm을 넘는 12,367행 모두 속도가 0보다 크다. 그래서 이 구간은 속도 신호가 0에 멈춘 이상이고, 품질 지표에는 잡히지 않는다. | 300 | 300 | 재현됨 | 5786~6085 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) AS pm, LAG(row_no) OVER (ORDER BY row_no) AS pr FROM sample_flags WHERE session_id=3 AND bad_ms=0), d AS (SELECT row_no, stm_ms-pm AS d, row_no-pr-1 AS nb FROM g WHERE pm IS NOT NULL) SELECT 100.0*SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END)/((SELECT COUNT(*) FROM sample WHERE session_id=3)+SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END)) AS missing_pct FROM d`
2. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) AS d FROM sample_flags WHERE session_id=3 AND bad_ms=0) SELECT COUNT(*) FROM g WHERE d < 0`
3. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) AS d FROM sample_flags WHERE session_id=3 AND bad_ms=0) SELECT d FROM g WHERE d > 1000 ORDER BY row_no`
4. `SELECT COUNT(*) FROM sample_flags WHERE session_id=3 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
5. `WITH r AS (SELECT bms_current*1.0/inv_dc_current AS q, ROW_NUMBER() OVER (ORDER BY bms_current*1.0/inv_dc_current) AS rn, COUNT(*) OVER () AS n FROM sample_flags WHERE session_id=3 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0) SELECT AVG(q) AS median_ratio FROM r WHERE rn IN ((n+1)/2,(n+2)/2)`
6. `WITH s AS (SELECT row_no FROM sample WHERE session_id=3 AND vehicle_speed_kmh=0 AND inv_motor_speed>500), t AS (SELECT row_no, row_no-ROW_NUMBER() OVER (ORDER BY row_no) AS g FROM s) SELECT COUNT(*), MIN(row_no), MAX(row_no) FROM t GROUP BY g ORDER BY COUNT(*) DESC`
