# 분석 에이전트 보고서: 시험2

AI가 도구를 31번 오가며 110초 동안 조사. 주장 8개 중 SQL 재실행으로 **8개 재현됨**.

## 요약

세션 '시험2'(32576행)의 누락률은 5.6451846488052135%(빠진 샘플 1949개)이고, 기록이 끊긴 구간은 0번, MCU 재시작은 2번이다. 깨진 행은 105개로 세션 전체의 0.322%이며, 이 중 시각(stm_ms)이 깨진 행이 60개다. 부하 구간의 bms_current/inv_dc_current 비율 중앙값은 0.7985611510791366으로, 1.25배 보정 계수 근거와 맞는다. 품질 지표에 안 잡힌 이상은 3곳을 찾았다. (1) 30336~30658행(323행): 인버터 DC 전류가 36.1 A에 멈췄는데, 같은 구간에서 팩 전류는 21.8~46.3 A로, 토크·회전수도 계속 변했다. (2) 28840~29139행(300행): 차량 속도는 0인데 모터 회전수는 평균 약 1374 rpm이었다. 구간 앞뒤 속도는 약 33~34 km/h라서 속도 신호가 빠진 것으로 보인다. (3) 21889~22188행(300행): 주 접촉기가 닫혀 있는데 인버터 전압이 팩 전압보다 평균 24.17 V 낮았다. 앞뒤 행에서는 두 전압 차이가 1 V 안쪽이었다. 11566~11653행에도 전압 불일치가 있지만, 이는 지표에 이미 있는 프리차지 미달 접촉기 닫힘 구간이다. 조향각이 오래 같은 값에 머문 구간(예: 2845~7657행)은 평균 속도가 0에 가까운 정차 중이어서 이상으로 보지 않았다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 5.6451846488052135
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.7985611510791366

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률** 규칙 3에 따라 계산한 누락률은 5.6451846488052135%다(빠진 샘플 1949개, 받은 샘플 32576개). 기록이 끊긴 구간(d>1000ms)은 없다. | 5.6451846488052135 | 5.6451846488052135 | 재현됨 |  |
| 2 | **MCU 재시작** bad_ms 행을 뺀 뒤 앞 행과의 stm_ms 차이가 음수인 경우가 2번 있다. 주행 중 MCU가 2번 재시작했다. | 2 | 2 | 재현됨 |  |
| 3 | **시각(stm_ms) 깨진 행** stm_ms가 깨진 행(bad_ms=1)은 60개다. | 60 | 60 | 재현됨 |  |
| 4 | **깨진 행 수** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 깨진 행은 105개로, 세션 전체 32576행의 0.322%다. 경고 기준 0.05%를 넘는다. | 105 | 105 | 재현됨 |  |
| 5 | **부하 구간 팩/인버터 전류비 중앙값** 부하 구간(inv_dc_current>25 A, bad_inv·bad_bms 행 제외, 7217행)의 bms_current/inv_dc_current 중앙값은 0.7985611510791366이다. 1.25배 스케일 보정 근거와 맞는다. | 0.7985611510791366 | 0.7985611510791366 | 재현됨 |  |
| 6 | **인버터 DC 전류 고착** 30336~30658행(323행) 동안 inv_dc_current가 36.1 A 한 값에 멈춰 있다. 부하 중 다른 고착 구간은 길어야 30행이다. 같은 구간에서 bms_current는 21.8~46.3 A로, inv_torque_feedback은 28가지 값으로 계속 변해서 두 전류 신호가 서로 맞지 않는다. 이 구간은 품질 지표의 전류 불일치(최장 14행)에 잡히지 않는다. | 323 | 323 | 재현됨 | 30336~30658 |
| 7 | **차량 속도 0인데 모터 회전 중** 28840~29139행(300행) 동안 vehicle_speed_kmh는 0이지만 inv_motor_speed는 500 rpm을 넘는다(평균 약 1373.5 rpm). 구간 직전(28839행)은 34.35 km/h, 직후(29140행)는 33.127 km/h라서, 이 구간에서 속도 신호만 0으로 떨어졌다. | 300 | 300 | 재현됨 | 28840~29139 |
| 8 | **접촉기 닫힘 중 인버터 전압과 팩 전압 불일치** 21889~22188행(300행) 동안 주 접촉기가 닫혀 있고 약 61 km/h로 주행 중인데, inv_voltage가 bms_voltage보다 평균 24.171666666666667 V 낮다. 구간 직전(21888행: 278.3 대 277.9 V)과 직후(22189행: 282.0 대 278.1 V)에는 차이가 몇 V 이내다. | 24.171666666666667 | 24.171666666666667 | 재현됨 | 21889~22188 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) AS ps, LAG(row_no) OVER (ORDER BY row_no) AS pr FROM sample_flags WHERE session_id=2 AND bad_ms=0), m AS (SELECT SUM(CASE WHEN stm_ms-ps>15 AND stm_ms-ps<=1000 THEN MAX(ROUND((stm_ms-ps)/10.0)-1-(row_no-pr-1),0) ELSE 0 END) AS miss FROM g) SELECT miss*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=2)+miss) AS pct FROM m`
2. `WITH g AS (SELECT stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) AS d FROM sample_flags WHERE session_id=2 AND bad_ms=0) SELECT SUM(CASE WHEN d<0 THEN 1 ELSE 0 END) FROM g`
3. `SELECT COUNT(*) FROM sample_flags WHERE session_id=2 AND bad_ms=1`
4. `SELECT COUNT(*) FROM sample_flags WHERE session_id=2 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
5. `WITH r AS (SELECT bms_current*1.0/inv_dc_current AS x, ROW_NUMBER() OVER (ORDER BY bms_current*1.0/inv_dc_current) AS rn, COUNT(*) OVER () AS c FROM sample_flags WHERE session_id=2 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0) SELECT AVG(x) FROM r WHERE rn IN ((c+1)/2,(c+2)/2)`
6. `SELECT COUNT(*) FROM sample WHERE session_id=2 AND row_no BETWEEN 30336 AND 30658 AND inv_dc_current=36.1`
7. `SELECT COUNT(*) FROM sample WHERE session_id=2 AND row_no BETWEEN 28840 AND 29139 AND vehicle_speed_kmh<1 AND inv_motor_speed>500`
8. `SELECT AVG(bms_voltage-inv_voltage) FROM sample WHERE session_id=2 AND row_no BETWEEN 21889 AND 22188`
