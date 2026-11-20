# 분석 에이전트 보고서: 시험1

AI가 도구를 24번 오가며 98초 동안 조사. 주장 8개 중 SQL 재실행으로 **8개 재현됨**.

## 요약

세션 '시험1'(16,869행)의 품질 지표는 도구로 다시 계산해 확인했다. 누락률은 10.185283782344799%(빠진 샘플 1,913개)로 경고 기준 8%를 넘는다. 깨진 행은 103개(0.611%)이고 MCU 재시작은 2번(row 5174, row 16014)이다. 기록이 멈춘 구간도 2번 있다(row 8066 직전 43,960 ms, row 8142 직전 1,259 ms). 부하 구간의 bms_current/inv_dc_current 비율 중앙값은 0.7967072297780959다. 지표에 잡히지 않은 이상이 하나 있다. row 11158~11457의 300행 동안 vehicle_speed_kmh가 0.0에 멈춰 있었는데, 같은 구간에서 inv_motor_speed는 1269~2294 rpm으로 돌고 있었다. 바로 앞 row 11157은 51.002 km/h, 바로 뒤 row 11458은 32.949 km/h였다. 그래서 차량 속도 신호가 멈춘 것으로 보이며, 이 구간은 bad_speed와 bad_value 표시가 모두 0이라 품질 지표에 빠져 있다. 접촉기가 닫힌 row 4925에서는 inv_voltage/bms_voltage 비율이 0.1625로, 프리차지가 덜 된 상태에서 닫혔다(지표의 프리차지_미달 1건과 같은 행). 조향각이 -0.5에 멈춘 row 3057~5680 구간은 모터 회전수와 횡가속도가 거의 0인 정차 구간이라 이상으로 보지 않았다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 10.185283782344799
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.7967072297780959

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률 8% 초과** bad_ms 행을 빼고 stm_ms 간격으로 계산하면 빠진 샘플은 1,913개다. 누락률은 10.185283782344799%로 경고 기준 8%를 넘는다. | 10.185283782344799 | 10.185283782344799 | 재현됨 |  |
| 2 | **MCU 재시작 2번** 앞 행보다 stm_ms가 줄어든 곳이 2곳 있다. row 5174(-208,590 ms)와 row 16014(-184,968 ms)로, 주행 중 MCU가 2번 재시작했다. | 2 | 2 | 재현됨 | 5174~16014 |
| 3 | **기록이 멈춘 구간 2번** 앞 행과의 간격이 1,000 ms를 넘는 곳이 2곳 있다. row 8066(43,960 ms)과 row 8142(1,259 ms)다. | 2 | 2 | 재현됨 | 8066~8142 |
| 4 | **깨진 행 103개** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행은 103개다. 세션 전체의 0.611%로 경고 기준 0.05%를 넘는다. | 103 | 103 | 재현됨 |  |
| 5 | **시각(stm_ms) 깨진 행 60개** sample_flags에서 bad_ms=1인 행은 60개다. | 60 | 60 | 재현됨 |  |
| 6 | **팩 전류/인버터 전류 비율 중앙값** 부하 구간(inv_dc_current > 25 A, bad_inv·bad_bms 행 제외, 4,242행)에서 bms_current/inv_dc_current 비율의 중앙값은 0.7967072297780959다. 스케일 계수 1.25가 빠져 있다는 보정 근거와 맞는다. | 0.7967072297780959 | 0.7967072297780959 | 재현됨 |  |
| 7 | **차량 속도 신호가 0에 멈춤 (지표에 안 잡힘)** row 11158~11457의 300행 동안 vehicle_speed_kmh가 0.0으로 고정돼 있다. 같은 구간에서 inv_motor_speed는 1269~2294 rpm이었다. 앞 행(11157)은 51.002 km/h, 뒤 행(11458)은 32.949 km/h다. 세션 전체에서 속도 0과 모터 1000 rpm 초과가 겹치는 행은 이 300행뿐이고, 이 구간에는 bad_speed·bad_value 표시가 없다. | 300 | 300 | 재현됨 | 11158~11457 |
| 8 | **프리차지가 덜 된 상태에서 메인 접촉기가 닫힘** 접촉기가 처음 닫힌 row 4925에서 inv_voltage는 46.3 V, bms_voltage는 284.9 V였다. 전압비는 약 0.163이다. 이어서 row 5011까지 inv_voltage가 46.3 V에서 230.5 V로 단계적으로 올라간다. | 0.16251316251316253 | 0.16251316251316253 | 재현됨 | 4925~5011 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, CAST(stm_ms AS REAL) ms FROM sample_flags WHERE session_id=1 AND bad_ms=0), d AS (SELECT row_no, ms - LAG(ms) OVER (ORDER BY row_no) d, row_no - LAG(row_no) OVER (ORDER BY row_no) - 1 nb FROM g), m AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) miss FROM d) SELECT miss*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=1)+miss) FROM m`
2. `WITH g AS (SELECT row_no, CAST(stm_ms AS REAL) ms FROM sample_flags WHERE session_id=1 AND bad_ms=0), d AS (SELECT row_no, ms - LAG(ms) OVER (ORDER BY row_no) d FROM g) SELECT COUNT(*) FROM d WHERE d<0`
3. `WITH g AS (SELECT row_no, CAST(stm_ms AS REAL) ms FROM sample_flags WHERE session_id=1 AND bad_ms=0), d AS (SELECT row_no, ms - LAG(ms) OVER (ORDER BY row_no) d FROM g) SELECT COUNT(*) FROM d WHERE d>1000`
4. `SELECT COUNT(*) FROM sample_flags WHERE session_id=1 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
5. `SELECT COUNT(*) FROM sample_flags WHERE session_id=1 AND bad_ms=1`
6. `WITH b AS (SELECT bms_current*1.0/inv_dc_current r FROM sample_flags WHERE session_id=1 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT r, ROW_NUMBER() OVER (ORDER BY r) rn, COUNT(*) OVER () c FROM b) SELECT AVG(r) FROM o WHERE rn IN ((c+1)/2,(c+2)/2)`
7. `SELECT COUNT(*) FROM sample WHERE session_id=1 AND vehicle_speed_kmh=0 AND inv_motor_speed>1000 AND row_no BETWEEN 11158 AND 11457`
8. `SELECT MIN(inv_voltage*1.0/bms_voltage) FROM sample WHERE session_id=1 AND motor_main_contactor=1 AND row_no=4925`
