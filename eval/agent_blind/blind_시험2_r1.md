# 분석 에이전트 보고서: 시험2

AI가 도구를 25번 오가며 79초 동안 조사. 주장 6개 중 SQL 재실행으로 **6개 재현됨**.

## 요약

세션 '시험2'(32,576행)를 조사했다. 빠진 샘플은 1,949개이고 누락률은 5.6451846488052135%로, 경고 기준 8%보다 낮다. 깨진 행은 105개(0.3223231827111984%)로 기준 0.05%를 넘는다. 이 중 stm_ms(MCU 시계)가 깨진 행이 60개다. MCU 재시작은 2번으로, 12093행과 18233행에서 stm_ms가 뒤로 돌아갔다. 부하 구간(7,217행)에서 bms_current/inv_dc_current 비율의 중앙값은 0.7985611510791366이다. 품질 지표에 안 잡히는 이상도 하나 찾았다. 28840~29139행(연속 300행)에서 vehicle_speed_kmh가 0인데, 같은 시간에 inv_motor_speed는 1205~1545 rpm으로 돌고 있었다. 이 구간 바로 앞(28839행)은 34.35 km/h, 바로 뒤(29140행)는 33.127 km/h다. 300행 가운데 bad_speed로 표시된 행은 0개라서, 품질 지표의 튄 값 검사로는 잡히지 않는다. 같은 조건(속도 0, 모터 500 rpm 넘음)의 행은 시험1과 시험3에도 각각 300행씩 있었다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 5.6451846488052135
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.7985611510791366

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률** 규칙 3에 따라 bad_ms 행을 빼고 stm_ms 간격으로 계산했다. 빠진 샘플은 1,949개이고, 받은 샘플 32,576개와 합친 값 대비 누락률은 5.6451846488052135%다. 경고 기준 8%보다 낮다. | 5.6451846488052135 | 5.6451846488052135 | 재현됨 |  |
| 2 | **깨진 행 수** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행이 105개로, 전체의 0.3223231827111984%다. 경고 기준 0.05%를 넘는다. | 105 | 105 | 재현됨 |  |
| 3 | **MCU 시계(stm_ms)가 깨진 행** stm_ms 값이 깨진(bad_ms=1) 행은 60개다. | 60 | 60 | 재현됨 |  |
| 4 | **MCU 재시작 2번** bad_ms 행을 뺀 뒤 앞 행과의 stm_ms 간격이 음수인 곳이 2곳이다. 12093행에서는 264372에서 52900으로, 18233행에서는 118270에서 39266으로 돌아갔다. | 2 | 2 | 재현됨 | 12093~18233 |
| 5 | **부하 구간 팩 전류/인버터 전류 비율 중앙값** 부하 구간(inv_dc_current > 25 A, bad_inv와 bad_bms 행은 뺌) 7,217행에서 보정 전 bms_current/inv_dc_current 비율의 중앙값은 0.7985611510791366이다. 보정 계수 1.25의 근거인 약 0.80과 맞는다. | 0.7985611510791366 | 0.7985611510791366 | 재현됨 |  |
| 6 | **지표에 안 잡힌 이상: 모터가 도는데 차량 속도 0** 28840~29139행(연속 300행)에서 vehicle_speed_kmh가 0이다. 같은 구간에서 inv_motor_speed는 1205~1545 rpm으로 돌고 있었다. 바로 앞 28839행은 34.35 km/h, 바로 뒤 29140행은 33.127 km/h라서 속도 신호만 300행 동안 0으로 끊긴 것이다. 이 구간에서 bad_speed=1인 행은 0개라서 품질 지표의 속도 튐 검사에 잡히지 않는다. 세션 전체에서 속도 0이면서 모터가 500 rpm을 넘는 행은 이 300행뿐이다. | 300 | 300 | 재현됨 | 28840~29139 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms FROM sample_flags WHERE session_id=2 AND bad_ms=0), d AS (SELECT stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) AS d, row_no - LAG(row_no) OVER (ORDER BY row_no) - 1 AS nb FROM g), m AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) AS miss FROM d) SELECT miss*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=2)+miss) AS missing_rate_pct FROM m`
2. `SELECT COUNT(*) AS broken_rows, COUNT(*)*100.0/(SELECT COUNT(*) FROM sample WHERE session_id=2) AS pct FROM sample_flags WHERE session_id=2 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
3. `SELECT COUNT(*) FROM sample_flags WHERE session_id=2 AND bad_ms=1`
4. `WITH g AS (SELECT row_no, stm_ms FROM sample_flags WHERE session_id=2 AND bad_ms=0), d AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) AS d FROM g) SELECT COUNT(*) AS restarts, MIN(row_no), MAX(row_no) FROM d WHERE d<0`
5. `WITH r AS (SELECT bms_current*1.0/inv_dc_current AS x FROM sample_flags WHERE session_id=2 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT x, ROW_NUMBER() OVER (ORDER BY x) rn, COUNT(*) OVER () n FROM r) SELECT AVG(x) AS median FROM o WHERE rn IN ((n+1)/2, (n+2)/2)`
6. `SELECT COUNT(*) AS rows_speed0_motor_spinning, MIN(row_no), MAX(row_no), MIN(inv_motor_speed), MAX(inv_motor_speed) FROM sample WHERE session_id=2 AND vehicle_speed_kmh=0 AND inv_motor_speed>500`
