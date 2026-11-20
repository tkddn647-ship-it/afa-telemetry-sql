# 분석 에이전트 보고서: 시험3

AI가 도구를 42번 오가며 165초 동안 조사. 주장 10개 중 SQL 재실행으로 **10개 재현됨**.

## 요약

시험3(session_id=3, 24061행)의 품질 지표를 SQL로 다시 계산해 보니 모두 일치했다. 누락률은 10.617%로 경고 기준인 8%를 넘고, 깨진 행은 107개(0.445%)다. 기록이 멈춘 구간이 1번(row 557, 4659 ms) 있고, MCU 재시작이 4번(row 17710, 19248, 19712, 23397) 있다. 부하 구간에서 bms_current/inv_dc_current 비율의 중앙값은 0.79585다. 지표에 잡히지 않는 이상은 네 가지를 찾았다. (1) row 5786–6085(300행)에서 모터는 1115–2900 rpm으로 도는데 vehicle_speed_kmh가 0에 멈춰 있다. 다른 구간에서는 속도가 모터 회전수의 약 0.02223배로 일정하다. (2) row 1–1791에서 접촉기는 닫힘(1)으로 찍히지만 인버터 신호(전압 279.0, 회전수 -14, 토크 -1.6)가 한 값에 멈춰 있다. 이 구간에서 stm_ms는 1791개가 모두 다르다. (3) MCU가 재시작하기 직전인 row 18955–19247(293행)에서 인버터 전압, 회전수, 토크와 조향각이 함께 멈춰 있다. (4) 조향각은 row 18258–19247(990행) 동안 -49.7에 멈춰 있는데, 그 사이 steering_speed가 0보다 큰 행이 7개 있다. 재시작 행인 19248에서 조향각은 -7.5로 한 번에 바뀐다. 참고로 재시작 뒤 row 19248–24061(4814행)은 끝까지 접촉기가 열려 있고 인버터 전압과 회전수가 0이다. BMS 전압은 271.3 V 이상으로 남아 있다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 10.617036294067388
- broken_timestamp_rows: 60
- mcu_restarts: 4
- pack_to_inverter_ratio_median: 0.79585326953748

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률 10.6% (경고 기준 8% 초과)** bad_ms가 아닌 행끼리 stm_ms 간격을 재면 빠진 샘플이 2858개이고, 누락률은 2858/(24061+2858)*100 = 10.617036294067388%다. | 10.617036294067388 | 10.617036294067388 | 재현됨 | 1~24061 |
| 2 | **MCU 재시작 4번** stm_ms가 앞 행보다 작아진 곳이 4번 있다. 위치는 row 17710, 19248, 19712, 23397이다. | 4 | 4 | 재현됨 | 17710~23397 |
| 3 | **기록이 멈춘 구간 1번 (4659 ms)** row 556과 557 사이의 stm_ms 간격이 4659 ms로 1000 ms를 넘는다. 기록이 멈춘 구간은 이 1번뿐이다. | 4659 | 4659.0 | 재현됨 | 556~557 |
| 4 | **깨진 행 107개 (0.445%)** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행이 107개로, 전체의 0.44470304642367314%다. 경고 기준 0.05%를 넘는다. 이 중 시각이 깨진 행(bad_ms)은 60개다. | 107 | 107 | 재현됨 |  |
| 5 | **팩 전류/인버터 전류 비율 중앙값 0.796** 부하 구간(inv_dc_current>25, bad_inv=0, bad_bms=0, 5964행)에서 보정 전 bms_current/inv_dc_current의 중앙값은 0.79585326953748이다. | 0.79585326953748 | 0.79585326953748 | 재현됨 |  |
| 6 | **모터가 도는데 차량 속도가 0에 멈춤 (row 5786–6085)** row 5786–6085의 300행 동안 inv_motor_speed는 1115–2900 rpm인데 vehicle_speed_kmh는 0이다. 바로 앞(row 5785)과 바로 뒤(row 6086)에서는 속도가 모터 회전수의 약 0.02223배다. 세션 전체에서 속도가 0인데 모터가 500 rpm을 넘는 행은 이 300행뿐이다. | 300 | 300 | 재현됨 | 5786~6085 |
| 7 | **로그 시작 구간에서 인버터 신호가 한 값에 멈춤 (row 1–1791)** row 1–1791의 1791행 모두에서 접촉기가 닫힘(1)인데, 인버터 값이 inv_voltage=279.0, inv_motor_speed=-14, inv_torque_feedback=-1.6으로 그대로다. 인버터 온도와 id/iq 피드백도 서로 다른 값이 1개뿐이다. 같은 구간에서 stm_ms는 1791개가 모두 다르고 x_g는 38가지 값이 나온다. row 1792에서는 접촉기가 0, 전압이 0으로 바뀐다. | 1791 | 1791 | 재현됨 | 1~1791 |
| 8 | **MCU 재시작 직전 인버터 신호와 조향각이 함께 멈춤 (row 18955–19247)** row 18955–19247의 293행 동안 접촉기는 닫힘(1)이고 inv_voltage=276.5, inv_motor_speed=6, inv_torque_feedback=0.1, steering_angle=-49.7이 바뀌지 않는다. 같은 구간에서 x_g는 62가지 값이 나온다. 다음 행인 19248이 MCU 재시작 위치다. | 293 | 293 | 재현됨 | 18955~19247 |
| 9 | **조향각이 -49.7에 멈춘 채 조향 속도가 나옴 (row 18258–19247)** row 18258–19247의 990행 동안 steering_angle은 -49.7로 그대로인데, 이 중 7행에서 steering_speed가 0보다 크다. 재시작 행인 19248에서 조향각은 -7.5로 한 번에 42.2만큼 바뀐다. | 990 | 990 | 재현됨 | 18258~19247 |
| 10 | **재시작 뒤 끝까지 인버터가 꺼진 상태 (row 19248–24061)** row 19248부터 마지막 행 24061까지 4814행 모두에서 접촉기가 0이고, inv_voltage와 inv_motor_speed가 0이다. 이 구간에서 BMS 전압은 최소 271.3 V로 남아 있다. | 4814 | 4814 | 재현됨 | 19248~24061 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms FROM sample_flags WHERE session_id=3 AND bad_ms=0), d AS (SELECT row_no, CAST(stm_ms AS REAL) - LAG(CAST(stm_ms AS REAL)) OVER (ORDER BY row_no) AS d, row_no - LAG(row_no) OVER (ORDER BY row_no) - 1 AS nb FROM g), m AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) AS miss FROM d) SELECT miss*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=3)+miss) AS missing_pct, miss FROM m`
2. `WITH g AS (SELECT row_no, stm_ms FROM sample_flags WHERE session_id=3 AND bad_ms=0), d AS (SELECT row_no, CAST(stm_ms AS REAL) - LAG(CAST(stm_ms AS REAL)) OVER (ORDER BY row_no) AS d FROM g) SELECT COUNT(*) AS restarts, GROUP_CONCAT(row_no) FROM d WHERE d<0`
3. `WITH g AS (SELECT row_no, stm_ms FROM sample_flags WHERE session_id=3 AND bad_ms=0), d AS (SELECT row_no, CAST(stm_ms AS REAL) - LAG(CAST(stm_ms AS REAL)) OVER (ORDER BY row_no) AS d FROM g) SELECT d AS gap_ms, row_no FROM d WHERE d>1000`
4. `SELECT COUNT(*) AS broken_rows, COUNT(*)*100.0/(SELECT COUNT(*) FROM sample WHERE session_id=3) AS pct FROM sample_flags WHERE session_id=3 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
5. `WITH r AS (SELECT CAST(bms_current AS REAL)/inv_dc_current AS x FROM sample_flags WHERE session_id=3 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT x, ROW_NUMBER() OVER (ORDER BY x) rn, COUNT(*) OVER () c FROM r) SELECT AVG(x) AS ratio_median FROM o WHERE rn IN ((c+1)/2, (c+2)/2)`
6. `SELECT COUNT(*) AS rows_speed0_motor_spinning, MIN(row_no), MAX(row_no), MIN(inv_motor_speed), MAX(inv_motor_speed) FROM sample WHERE session_id=3 AND vehicle_speed_kmh=0 AND inv_motor_speed>500`
7. `SELECT COUNT(*) AS frozen_rows, MIN(row_no), MAX(row_no) FROM sample WHERE session_id=3 AND row_no BETWEEN 1 AND 1791 AND motor_main_contactor=1 AND inv_voltage=279.0 AND inv_motor_speed=-14 AND inv_torque_feedback=-1.6`
8. `SELECT COUNT(*) AS frozen_rows, MIN(row_no), MAX(row_no) FROM sample WHERE session_id=3 AND row_no BETWEEN 18955 AND 19247 AND motor_main_contactor=1 AND inv_voltage=276.5 AND inv_motor_speed=6 AND inv_torque_feedback=0.1 AND steering_angle=-49.7`
9. `SELECT COUNT(*) AS stuck_rows, MIN(row_no), MAX(row_no), SUM(steering_speed>0) FROM sample WHERE session_id=3 AND row_no BETWEEN 18258 AND 19247 AND steering_angle=-49.7`
10. `SELECT COUNT(*) AS rows_open, MIN(row_no), MAX(row_no), MIN(bms_voltage) FROM sample WHERE session_id=3 AND row_no>=19248 AND motor_main_contactor=0 AND inv_voltage=0 AND inv_motor_speed=0`
