# 분석 에이전트 보고서: 시험2

AI가 도구를 26번 오가며 111초 동안 조사. 주장 7개 중 SQL 재실행으로 **7개 재현됨**.

## 요약

세션 '시험2'(32,576행)를 분석 규칙 v6에 따라 다시 계산했습니다. 누락률은 5.6451846488052135%(빠진 샘플 1949개), 시각이 깨진 행(bad_ms)은 60개, 깨진 행은 모두 105개입니다. MCU 재시작은 2번으로 row 12093과 row 18233이고, 부하 구간 bms_current/inv_dc_current 비율 중앙값은 0.7985611510791366입니다. 품질 지표에 잡히지 않는 이상도 하나 찾았습니다. row 28840~29139의 300행 동안 모터는 1205 rpm 이상으로 돌고 바퀴 속도와 조향각도 계속 변하는데 vehicle_speed_kmh만 0.0으로 떨어져 있습니다. 바로 앞뒤 행에서는 속도/모터 회전수 비율이 약 0.0222이므로 신호끼리 모순되는 구간입니다. 이 구간에는 bad_speed 표시가 하나도 없습니다. 차가 서 있을 때 값이 오래 같은 경우(예: 조향각, bms_voltage)나 모터 회전수가 CAN 주기 배수로 유지되는 경우는 정상 동작으로 보고 이상으로 넣지 않았습니다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 5.6451846488052135
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.7985611510791366

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **누락률** bad_ms 행을 빼고 stm_ms 간격으로 센 결과 빠진 샘플은 1949개이고, 누락률은 1949/(32576+1949)*100 = 5.6451846488052135%입니다. 멈춘 구간(간격 1000 ms 초과)은 0번입니다. | 5.6451846488052135 | 5.6451846488052135 | 재현됨 |  |
| 2 | **시각(stm_ms) 깨진 행** sample_flags에서 bad_ms=1인 행은 60개입니다. | 60 | 60 | 재현됨 |  |
| 3 | **깨진 행 합계** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행은 105개로, 전체 32576행의 약 0.322%입니다. 경고 기준 0.05%를 넘습니다. | 105 | 105 | 재현됨 |  |
| 4 | **MCU 재시작 2번** bad_ms 행을 뺀 상태에서 stm_ms가 앞 행보다 작아진 곳이 2군데입니다. row 12093(264372→52900)과 row 18233(118270→39266)입니다. | 2 | 2 | 재현됨 | 12093~18233 |
| 5 | **팩/인버터 전류 비율 중앙값** 부하 구간(inv_dc_current>25 A, bad_inv·bad_bms 행 제외, 7217행)에서 bms_current/inv_dc_current 비율의 중앙값은 0.7985611510791366입니다. 보정 계수 1.25의 근거인 '약 0.80'과 맞습니다. | 0.7985611510791366 | 0.7985611510791366 | 재현됨 |  |
| 6 | **차량 속도 0 고정 — 모터 회전수와 모순 (row 28840~29139)** row 28840부터 29139까지 300행이 이어지는 동안 vehicle_speed_kmh는 0.0인데 inv_motor_speed는 200 rpm을 넘습니다. 이 조건에 맞는 행은 세션 전체에서 이 구간뿐입니다. 바로 앞 row 28839의 속도는 34.35 km/h, 바로 뒤 row 29140은 33.127 km/h입니다. 구간 안에서 모터 회전수는 최소 1205 rpm이고, 바퀴 속도(fr, fl, rr, rl)와 조향각도 계속 변하고 inv_dc_current는 최대 38.2 A까지 흐릅니다. 차는 실제로 달리고 있었고 속도 신호만 0으로 떨어진 것입니다. 이 구간에서 bad_speed=1인 행은 0개라 품질 지표에는 잡히지 않습니다. | 300 | 300 | 재현됨 | 28840~29139 |
| 7 | **모순 구간 앞뒤의 속도/회전수 정상 비율** 모순 구간 바로 앞 100행(28740~28839)과 바로 뒤 100행(29140~29239)에서 vehicle_speed_kmh/inv_motor_speed 평균은 0.022232814320482838입니다. 이 비율이면 구간 안 회전수 1205 rpm 이상은 약 27 km/h 이상에 해당하므로, 속도 0.0은 모터 회전수와 맞지 않습니다. | 0.022232814320482838 | 0.022232814320482838 | 재현됨 | 28740~29239 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms FROM sample_flags WHERE session_id=2 AND bad_ms=0), d AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) AS d, row_no - LAG(row_no) OVER (ORDER BY row_no) - 1 AS nb FROM g), m AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) AS miss FROM d) SELECT miss*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=2)+miss) AS pct FROM m`
2. `SELECT COUNT(*) FROM sample_flags WHERE session_id=2 AND bad_ms=1`
3. `SELECT COUNT(*) FROM sample_flags WHERE session_id=2 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
4. `WITH g AS (SELECT row_no, stm_ms FROM sample_flags WHERE session_id=2 AND bad_ms=0), d AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) AS d FROM g) SELECT COUNT(*) FROM d WHERE d<0`
5. `WITH r AS (SELECT bms_current*1.0/inv_dc_current AS q FROM sample_flags WHERE session_id=2 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT q, ROW_NUMBER() OVER (ORDER BY q) rn, COUNT(*) OVER () c FROM r) SELECT AVG(q) AS median FROM o WHERE rn IN ((c+1)/2, (c+2)/2)`
6. `SELECT COUNT(*) FROM sample WHERE session_id=2 AND vehicle_speed_kmh=0 AND inv_motor_speed>200 AND row_no BETWEEN 28840 AND 29139`
7. `SELECT AVG(vehicle_speed_kmh/inv_motor_speed) FROM sample WHERE session_id=2 AND inv_motor_speed>200 AND (row_no BETWEEN 28740 AND 28839 OR row_no BETWEEN 29140 AND 29239)`
