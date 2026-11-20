# 분석 에이전트 보고서: 시험1

AI가 도구를 33번 오가며 92초 동안 조사. 주장 8개 중 SQL 재실행으로 **8개 재현됨**.

## 요약

세션 '시험1'(16,869행)을 조사했다. 경고 3건(누락률 10.185%, 깨진 행 103행, MCU 재시작 2번)은 run_select로 다시 계산해 모두 같은 값이 나왔다. 보정 계수가 정해진 근거인 부하 구간(4,242행)의 팩/인버터 전류비 중앙값은 0.7967이다. 행 4925에서 주 접촉기가 닫힐 때 인버터/팩 전압비는 0.1625였다. 프리차지가 덜 된 상태로 닫혔다는 뜻이다. 품질 지표에 잡히지 않는 이상도 하나 찾았다. row_no 11158~11457(300행)에서 vehicle_speed_kmh 가 계속 0.0인데 같은 행들의 inv_motor_speed 는 1269~2294 rpm이다. bad_speed 표시는 0이다. 바로 앞 행 11157은 51.0 km/h, 바로 뒤 행 11458은 32.9 km/h다. 나머지 정상 행에서는 속도/회전수 비가 0.0222로 일정했다. 따라서 이 300행은 속도 신호가 0으로 떨어진 구간으로, 튄 값 검사로는 걸러지지 않았다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 10.185283782344799
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.7967072297780959

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률 8% 초과** bad_ms 행을 뺀 뒤 stm_ms 간격으로 센 빠진 샘플은 1,913개다. 누락률은 1913/(16869+1913)*100 = 10.185%로 경고 기준 8%를 넘는다. | 10.185283782344799 | 10.185283782344799 | 재현됨 |  |
| 2 | **깨진 행 103행** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행은 103행이다. 전체 대비 0.611%로 기준 0.05%를 넘는다. | 103 | 103 | 재현됨 |  |
| 3 | **시각(stm_ms) 깨진 행 60행** stm_ms 값이 깨진 행(bad_ms=1)은 60행이다. | 60 | 60 | 재현됨 |  |
| 4 | **MCU 재시작 2번** 앞 행보다 stm_ms 가 줄어든 곳이 두 번 있다. row_no 5174에서 263172→54582 ms, row_no 16014에서 223892→38924 ms로 떨어졌다. 주행 중 MCU가 재시작한 것이다. | 2 | 2 | 재현됨 | 5174~16014 |
| 5 | **기록이 끊긴 구간 2번** 간격이 1000 ms를 넘은 곳이 두 번 있다. row_no 8066 앞이 43,960 ms, row_no 8142 앞이 1,259 ms다. | 2 | 2 | 재현됨 | 8066~8142 |
| 6 | **부하 구간 팩/인버터 전류비 중앙값 0.797** 부하 구간(inv_dc_current>25 A, bad_inv·bad_bms 제외)은 4,242행이다. 이 구간의 bms_current/inv_dc_current 중앙값은 0.7967로, 보정 계수 1.25를 정한 근거와 맞는다. | 0.7967072297780959 | 0.7967072297780959 | 재현됨 |  |
| 7 | **프리차지 미달 상태에서 접촉기 닫힘** 주 접촉기는 row_no 4925에서 0→1로 바뀐다. 이때 inv_voltage 46.3 V, bms_voltage 284.9 V로 전압비가 0.1625뿐이고 motor_precharge 는 0이다. 프리차지가 끝나기 전에 닫혔다. | 0.16251316251316253 | 0.16251316251316253 | 재현됨 | 4925~4925 |
| 8 | **[지표 밖 이상] 모터는 도는데 차량 속도가 0인 300행** row_no 11158~11457의 300행 내내 vehicle_speed_kmh 가 0.0이다. 같은 행의 inv_motor_speed 는 1269~2294 rpm으로 차가 달리고 있었다. bad_speed·bad_value 표시는 0이라 품질 지표에 잡히지 않는다. 앞 행 11157은 51.002 km/h, 뒤 행 11458은 32.949 km/h다. 다른 정상 행에서는 속도/회전수 비가 0.0222로 일정했으므로, 이 구간은 속도 신호가 0으로 떨어진 것이다. | 300 | 300 | 재현됨 | 11158~11457 |

## 근거 SQL

1. `WITH g AS (SELECT stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) d, row_no - LAG(row_no) OVER (ORDER BY row_no) - 1 nb FROM sample_flags WHERE session_id=1 AND bad_ms=0), m AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) miss FROM g) SELECT miss*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=1)+miss) FROM m`
2. `SELECT COUNT(*) FROM sample_flags WHERE session_id=1 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
3. `SELECT SUM(bad_ms) FROM sample_flags WHERE session_id=1`
4. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) d FROM sample_flags WHERE session_id=1 AND bad_ms=0) SELECT SUM(d<0), MIN(CASE WHEN d<0 THEN row_no END), MAX(CASE WHEN d<0 THEN row_no END) FROM g`
5. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) d FROM sample_flags WHERE session_id=1 AND bad_ms=0) SELECT SUM(d>1000), MIN(CASE WHEN d>1000 THEN row_no END), MAX(CASE WHEN d>1000 THEN row_no END) FROM g`
6. `WITH r AS (SELECT bms_current*1.0/inv_dc_current x, ROW_NUMBER() OVER (ORDER BY bms_current*1.0/inv_dc_current) k, COUNT(*) OVER () n FROM sample_flags WHERE session_id=1 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0) SELECT AVG(x), MAX(n) FROM r WHERE k IN ((n+1)/2, (n+2)/2)`
7. `WITH s AS (SELECT row_no, motor_main_contactor c, LAG(motor_main_contactor) OVER (ORDER BY row_no) p, inv_voltage*1.0/bms_voltage v FROM sample WHERE session_id=1) SELECT v, row_no FROM s WHERE p=0 AND c=1`
8. `SELECT COUNT(*) FROM sample_flags WHERE session_id=1 AND row_no BETWEEN 11158 AND 11457 AND vehicle_speed_kmh=0 AND inv_motor_speed>1000 AND bad_speed=0`
