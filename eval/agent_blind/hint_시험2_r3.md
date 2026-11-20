# 분석 에이전트 보고서: 시험2

AI가 도구를 31번 오가며 111초 동안 조사. 주장 7개 중 SQL 재실행으로 **7개 재현됨**.

## 요약

세션 '시험2'(32,576행)를 분석 규칙 v6에 따라 SQL로 다시 계산한 결과, 품질 지표와 값이 모두 맞았다. 누락률은 5.6451846488052135%(빠진 샘플 1,949개)이고, MCU 재시작은 2번(12093행, 18233행), 깨진 행은 105개(0.322%), 시각이 깨진 행(bad_ms)은 60개, 부하 구간의 bms_current/inv_dc_current 비율 중앙값은 0.7985611510791366이다. 품질 지표에 잡히지 않은 이상도 두 개 찾았다. (1) 28840~29139행(300행)에서는 모터가 1205~1545 rpm으로 돌고 있는데 vehicle_speed_kmh가 0으로 떨어져 있어 두 신호가 서로 모순된다. 이 구간의 bad_speed 표시는 0이다. (2) 30336~30658행(323행)에서는 모터 회전수(2743~3009 rpm), 토크 피드백(29.4~56.3), 팩 전류(21.8~46.3 A)가 계속 바뀌는데 inv_dc_current만 36.1 A에 멈춰 있다. 이 구간의 bad_inv와 bad_value도 0이다. 다른 신호는 정상 범위에서 몇십 행씩만 멈췄다(인버터 신호 최대 50행, 팩 전류 30행).

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 5.6451846488052135
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.7985611510791366

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률** bad_ms 행을 빼고 stm_ms 간격으로 계산하면 빠진 샘플이 1,949개이고, 누락률은 5.6451846488052135%이다. 기록이 멈춘 구간(d>1000)은 없다. | 5.6451846488052135 | 5.6451846488052135 | 재현됨 |  |
| 2 | **MCU 재시작 2번** stm_ms가 앞 행보다 줄어든 곳이 2군데다. 12093행에서는 -211472 ms, 18233행에서는 -79004 ms 줄었다. | 2 | 2 | 재현됨 | 12093~18233 |
| 3 | **깨진 행 105개** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행이 105개로, 전체의 0.322%이다. 경고 기준인 0.05%를 넘는다. | 105 | 105 | 재현됨 |  |
| 4 | **시각(stm_ms) 깨진 행 60개** stm_ms 값이 깨진 행(bad_ms=1)이 60개다. | 60 | 60 | 재현됨 |  |
| 5 | **부하 구간 팩/인버터 전류비 중앙값** 부하 구간(inv_dc_current>25 A, bad_inv·bad_bms 행 제외, 7,217행)에서 bms_current/inv_dc_current 비율의 중앙값은 0.7985611510791366이다. 보정 계수 1.25가 필요하다는 판단과 맞는다. | 0.7985611510791366 | 0.7985611510791366 | 재현됨 |  |
| 6 | **모터는 도는데 차량 속도가 0인 구간** 28840~29139행(300행 연속)에서는 inv_motor_speed가 1205~1545 rpm인데 vehicle_speed_kmh가 0이다. 바로 앞 28839행은 34.35 km/h, 바로 뒤 29140행은 33.127 km/h이고, 다른 구간의 속도/회전수 비율은 약 0.0222로 일정하다. 이 구간의 bad_speed 표시는 0이라 품질 지표에 잡히지 않았다. | 300 | 300 | 재현됨 | 28840~29139 |
| 7 | **인버터 DC 전류가 36.1 A에 멈춘 구간** 30336~30658행(323행 연속)에서 inv_dc_current가 36.1 A 그대로다. 같은 구간에서 inv_motor_speed는 2743~3009 rpm, inv_torque_feedback은 29.4~56.3, bms_current는 21.8~46.3 A(서로 다른 값 27개)로 계속 바뀐다. 0이 아닌 값에서 inv_dc_current가 이렇게 오래 멈춘 다른 구간은 최대 50행이다. 이 구간의 bad_inv와 bad_value는 0이라 품질 지표에 잡히지 않았다. | 323 | 323 | 재현됨 | 30336~30658 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, CAST(stm_ms AS REAL) ms FROM sample_flags WHERE session_id=2 AND bad_ms=0), d AS (SELECT row_no, ms - LAG(ms) OVER (ORDER BY row_no) d, row_no - LAG(row_no) OVER (ORDER BY row_no) - 1 nb FROM g), t AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) m FROM d) SELECT m*100.0/(m+(SELECT COUNT(*) FROM sample WHERE session_id=2)) FROM t`
2. `WITH g AS (SELECT row_no, CAST(stm_ms AS REAL) ms FROM sample_flags WHERE session_id=2 AND bad_ms=0), d AS (SELECT row_no, ms - LAG(ms) OVER (ORDER BY row_no) d FROM g) SELECT COUNT(*), MIN(row_no), MAX(row_no) FROM d WHERE d<0`
3. `SELECT COUNT(*) FROM sample_flags WHERE session_id=2 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
4. `SELECT COUNT(*) FROM sample_flags WHERE session_id=2 AND bad_ms=1`
5. `SELECT bms_current*1.0/inv_dc_current r FROM sample_flags WHERE session_id=2 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0 ORDER BY r LIMIT 1 OFFSET (SELECT (COUNT(*)-1)/2 FROM sample_flags WHERE session_id=2 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0)`
6. `WITH s AS (SELECT row_no, CASE WHEN vehicle_speed_kmh=0 AND inv_motor_speed>500 THEN 1 ELSE 0 END bad FROM sample WHERE session_id=2), g AS (SELECT row_no, row_no - ROW_NUMBER() OVER (ORDER BY row_no) grp FROM s WHERE bad=1) SELECT COUNT(*) n, MIN(row_no), MAX(row_no) FROM g GROUP BY grp ORDER BY n DESC LIMIT 1`
7. `WITH s AS (SELECT row_no, inv_dc_current v, CASE WHEN inv_dc_current IS LAG(inv_dc_current) OVER (ORDER BY row_no) THEN 0 ELSE 1 END chg FROM sample WHERE session_id=2), g AS (SELECT *, SUM(chg) OVER (ORDER BY row_no) grp FROM s) SELECT COUNT(*) n, MIN(row_no), MAX(row_no), v FROM g WHERE ABS(v)>1 GROUP BY grp ORDER BY n DESC LIMIT 1`
