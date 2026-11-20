# 분석 에이전트 보고서: 시험1

AI가 도구를 32번 오가며 132초 동안 조사. 주장 9개 중 SQL 재실행으로 **9개 재현됨**.

## 요약

세션 '시험1'(16,869행)을 분석 규칙 v6에 따라 조사했다. 샘플 누락률은 10.185%(빠진 샘플 1,913개)로 경고 기준 8%를 넘는다. 깨진 행은 103개(0.611%)다. MCU 재시작은 2번(row 5174, 16014), 기록이 끊긴 구간은 2번(row 8066, 8142)이다. 부하 구간의 bms_current/inv_dc_current 비율 중앙값은 0.7967로, 보정 계수 1.25와 맞는다. 품질 지표에 안 잡히는 이상도 3가지 찾았다. (1) row 11158~11457(300행)에서 모터는 1269~2294 rpm으로 도는데 차속이 정확히 0이다. 이 행들에는 깨진 값 표시가 없다. (2) bms_charge(SOC)가 세션 전체 16,869행에서 0에 고정돼 있다. (3) bms_voltage가 row 1~4941에서 284.9 V 한 값에 멈춰 있다. 이 밖에 메인 접촉기가 row 4925에서 닫힐 때 인버터/팩 전압비가 0.1625여서 프리차지가 덜 된 상태였다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 10.185283782344799
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.7967072297780959

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률 10.185%** bad_ms 60행을 빼고 stm_ms 간격으로 계산하면 빠진 샘플은 1,913개다. 누락률은 1913/(16869+1913)*100 = 10.185%로 경고 기준 8%를 넘는다. | 10.185283782344799 | 10.185283782344799 | 재현됨 |  |
| 2 | **깨진 행 103개 (시각 깨짐 60행 포함)** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행은 103개로, 전체의 0.611%다. 이 가운데 stm_ms가 깨진 행(bad_ms)은 60개다. | 103 | 103 | 재현됨 |  |
| 3 | **MCU 재시작 2번** stm_ms가 뒤로 간 곳이 2곳이다. row 5174에서 -208,590 ms, row 16014에서 -184,968 ms 뛰었다. 주행 중 MCU가 2번 재시작한 것이다. | 2 | 2 | 재현됨 | 5174~16014 |
| 4 | **기록 멈춘 구간 2번** 간격이 1000 ms를 넘는 곳이 2곳이다. row 8066 앞에서 43,960 ms, row 8142 앞에서 1,259 ms 동안 기록이 끊겼다. 규칙에 따라 이 구간은 누락으로 세지 않았다. | 2 | 2 | 재현됨 | 8066~8142 |
| 5 | **부하 구간 팩/인버터 전류비 중앙값 0.7967** 부하 구간(inv_dc_current>25 A, bad_inv와 bad_bms 뺌) 4,242행에서 bms_current/inv_dc_current 비율의 중앙값은 0.7967이다. scale_correction 표의 계수 1.25(=1/0.8)와 맞는다. | 0.7967072297780959 | 0.7967072297780959 | 재현됨 |  |
| 6 | **차속 0인데 모터 회전 (신호 모순, 지표에 안 잡힘)** row 11158~11457의 300행에서 inv_motor_speed는 1269~2294 rpm인데 vehicle_speed_kmh는 0.0으로 고정돼 있다. 바로 앞 row 11157은 51.0 km/h, 바로 뒤 row 11458은 32.9 km/h다. 이 300행에는 bad_speed와 bad_value가 모두 0이라 품질 지표에 잡히지 않는다. | 300 | 300 | 재현됨 | 11158~11457 |
| 7 | **bms_charge(SOC)가 세션 전체에서 0에 고정** bms_charge는 row 1~16869 전 행에서 0이다. 부하 행이 4,259개 있는데도 값이 한 번도 바뀌지 않는다. SOC 신호가 기록되지 않거나 멈춘 것이다. | 16869 | 16869 | 재현됨 | 1~16869 |
| 8 | **bms_voltage가 row 1~4941에서 284.9 V에 멈춤** 세션 시작부터 row 4941까지 4,941행 동안 bms_voltage는 284.9 V 한 값이다. 이 구간 inv_voltage는 최대 89.6 V로, 대부분 고전압이 연결되기 전이다. 나머지 구간에서는 bms_voltage가 273.8~288.3 V 사이 87개 값으로 변한다. | 4941 | 4941 | 재현됨 | 1~4941 |
| 9 | **접촉기가 프리차지 미달 상태에서 닫힘** motor_main_contactor가 0에서 1로 바뀐 것은 row 4925 한 번이다. 이때 inv_voltage는 46.3 V, bms_voltage는 284.9 V로 전압비가 0.1625밖에 안 된다. 프리차지가 덜 된 상태에서 메인 접촉기가 닫혔다. | 0.16251316251316253 | 0.16251316251316253 | 재현됨 | 4925~4925 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, CAST(stm_ms AS REAL) ms FROM sample_flags WHERE session_id=1 AND bad_ms=0), d AS (SELECT row_no, ms - LAG(ms) OVER (ORDER BY row_no) d, row_no - LAG(row_no) OVER (ORDER BY row_no) - 1 nb FROM g) SELECT 100.0*SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END)/((SELECT COUNT(*) FROM sample WHERE session_id=1) + SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END)) AS miss_pct FROM d`
2. `SELECT SUM(bad_ms OR bad_inv OR bad_bms OR bad_speed OR bad_value) AS broken, SUM(bad_ms) AS bad_ms_rows FROM sample_flags WHERE session_id=1`
3. `WITH g AS (SELECT row_no, CAST(stm_ms AS REAL) ms FROM sample_flags WHERE session_id=1 AND bad_ms=0), d AS (SELECT row_no, ms - LAG(ms) OVER (ORDER BY row_no) d FROM g) SELECT SUM(d<0) AS restarts, MIN(CASE WHEN d<0 THEN row_no END), MAX(CASE WHEN d<0 THEN row_no END) FROM d`
4. `WITH g AS (SELECT row_no, CAST(stm_ms AS REAL) ms FROM sample_flags WHERE session_id=1 AND bad_ms=0), d AS (SELECT row_no, ms - LAG(ms) OVER (ORDER BY row_no) d FROM g) SELECT SUM(d>1000) AS stalls, MIN(CASE WHEN d>1000 THEN row_no END), MAX(CASE WHEN d>1000 THEN row_no END) FROM d`
5. `WITH r AS (SELECT bms_current*1.0/inv_dc_current x FROM sample_flags WHERE session_id=1 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT x, ROW_NUMBER() OVER (ORDER BY x) i, COUNT(*) OVER () c FROM r) SELECT AVG(x) AS median FROM o WHERE i IN ((c+1)/2, (c+2)/2)`
6. `SELECT COUNT(*) AS n, MIN(row_no), MAX(row_no) FROM sample_flags WHERE session_id=1 AND inv_motor_speed>300 AND vehicle_speed_kmh=0 AND bad_speed=0 AND bad_value=0`
7. `SELECT COUNT(*) FROM sample WHERE session_id=1 AND bms_charge=0`
8. `SELECT COUNT(*) AS n, COUNT(DISTINCT bms_voltage) nd, MIN(bms_voltage), MAX(inv_voltage) FROM sample WHERE session_id=1 AND row_no BETWEEN 1 AND 4941`
9. `WITH s AS (SELECT row_no, motor_main_contactor c, LAG(motor_main_contactor) OVER (ORDER BY row_no) pc, inv_voltage, bms_voltage FROM sample WHERE session_id=1) SELECT inv_voltage/bms_voltage AS ratio, row_no FROM s WHERE c=1 AND pc=0`
