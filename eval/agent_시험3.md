# 분석 에이전트 보고서: 시험3

AI가 도구를 28번 오가며 113초 동안 조사. 주장 9개 중 SQL 재실행으로 **9개 재현됨**.

## 요약

세션 '시험3'(24,061행) 품질 분석. 지표 4개가 경고 기준을 넘었다. 누락률은 10.617%(기준 8%), 깨진 행은 108개로 0.449%(기준 0.05%), MCU 재시작은 4번(row 17710, 19248, 19712, 23397), 보정 뒤 위반 비율은 34.4%(기준 30%)다. 기록이 멈춘 구간은 1번(row 557, stm_ms 간격 4,659 ms) 있다. 부하 구간의 bms_current/inv_dc_current 비율 중앙값은 0.79362다. 지표에 잡히지 않은 이상도 찾았다. row 5177~5481의 305행에서 inv_dc_current가 81.8 A에 멈춰 있다. 같은 구간에서 bms_current는 -3.2~110.3 A, 토크 피드백은 -3.1~142.7 사이에서 계속 바뀐다. 그중 98행은 팩 전류가 5 A 미만인데도 인버터 전류가 81.8 A로 기록되어 두 신호가 서로 맞지 않는다. 이 305행은 bad_inv=0이라서 부하 구간 6,109행에 모두 들어가 있고, 따라서 비율과 위반 지표에도 섞여 있다. 그 밖에 row 2751~2780에서는 인버터 신호(모터 속도, DC 전류, 전압)가 30행 동안 함께 같은 값을 유지했다. 다른 구간에서는 보통 약 10행마다 값이 바뀐다. 조향각이 오래 같은 값인 구간(예: row 1~2291)은 평균 속도가 거의 0이고 인버터 전류도 거의 0이라 정차 중으로 보고 이상으로 세지 않았다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 10.617036294067388
- broken_timestamp_rows: 60
- mcu_restarts: 4
- pack_to_inverter_ratio_median: 0.7936170212765958

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률 10.6%** 규칙 3에 따라 bad_ms 행을 빼고 계산하면 빠진 샘플은 2,858개, 누락률은 10.617%로 경고 기준 8%를 넘는다. | 10.617036294067388 | 10.617036294067388 | 재현됨 |  |
| 2 | **깨진 행 108개** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행은 108개로, 전체의 0.449%다(기준 0.05%). | 108 | 108 | 재현됨 |  |
| 3 | **MCU 재시작 4번** stm_ms가 앞 행보다 작아진 곳이 4번 있다(row 17710, 19248, 19712, 23397). | 4 | 4 | 재현됨 | 17710~23397 |
| 4 | **기록 멈춤 1번** row 557에서 앞 행과의 stm_ms 간격이 4,659 ms(983433→988092)로 1,000 ms를 넘는다. 기록이 멈춘 구간 1번이다. | 1 | 1 | 재현됨 | 557~557 |
| 5 | **부하 구간 팩/인버터 전류비 중앙값 0.794** 부하 구간(inv_dc_current>25, bad_inv와 bad_bms 행 제외) 6,109행에서 보정 전 bms_current/inv_dc_current 비율의 중앙값은 0.79362다. | 0.7936170212765958 | 0.7936170212765958 | 재현됨 |  |
| 6 | **인버터 DC 전류가 81.8 A에 멈춤** row 5177~5481의 305행 내내 inv_dc_current가 81.8 A로 같다. 같은 구간에서 bms_current는 34가지, inv_motor_speed는 27가지, inv_voltage는 26가지 값으로 계속 바뀐다. 0이 아닌 값이 이어진 길이로는 다음으로 긴 구간(39행)보다 훨씬 길다. 품질 지표에는 잡히지 않았다. | 305 | 305 | 재현됨 | 5177~5481 |
| 7 | **멈춘 인버터 전류와 팩 전류가 서로 맞지 않음** 같은 구간(row 5177~5481)에서 inv_dc_current는 81.8 A인데 bms_current는 5 A 미만인 행이 98개 있다. 토크 피드백도 0 이하로 내려간 행이 70개 있어, 인버터 전류 값이 실제 부하를 반영하지 않는다. | 98 | 98 | 재현됨 | 5177~5481 |
| 8 | **멈춘 구간이 부하 구간 지표에 섞임** 멈춘 305행은 모두 bad_inv=0, bad_bms=0이고 inv_dc_current>25라서 부하 구간(6,109행)에 들어간다. 그래서 비율 중앙값과 보정 전후 위반 비율 계산에 이 행들이 포함된다. | 305 | 305 | 재현됨 | 5177~5481 |
| 9 | **인버터 신호 30행 동시 정지** row 2751~2780(stm_ms 1011882~1012182)에서 inv_motor_speed(770), inv_dc_current(-0.1), inv_voltage, vehicle_speed_kmh가 30행 동안 함께 같은 값을 유지했다. 그동안 x_g는 28가지 값으로 바뀌었다. 같은 패턴이 row 7032~7061에서도 30행 동안 나타난다. 다른 구간에서는 인버터 값이 보통 약 10행마다 바뀐다. | 30 | 30 | 재현됨 | 2751~2780 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) ps, LAG(row_no) OVER (ORDER BY row_no) pr FROM sample_flags WHERE session_id=3 AND bad_ms=0), m AS (SELECT stm_ms-ps d, row_no-pr-1 nb FROM g WHERE ps IS NOT NULL), t AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) miss FROM m) SELECT 100.0*miss/((SELECT COUNT(*) FROM sample WHERE session_id=3)+miss) FROM t`
2. `SELECT COUNT(*) FROM sample_flags WHERE session_id=3 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
3. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) d FROM sample_flags WHERE session_id=3 AND bad_ms=0) SELECT SUM(d<0), SUM(d>1000) FROM g`
4. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) d FROM sample_flags WHERE session_id=3 AND bad_ms=0) SELECT SUM(d>1000) FROM g`
5. `WITH l AS (SELECT bms_current*1.0/inv_dc_current r FROM sample_flags WHERE session_id=3 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT r, ROW_NUMBER() OVER (ORDER BY r) rn, COUNT(*) OVER () c FROM l) SELECT AVG(r) FROM o WHERE rn IN ((c+1)/2,(c+2)/2)`
6. `SELECT COUNT(*) FROM sample WHERE session_id=3 AND row_no BETWEEN 5177 AND 5481 AND inv_dc_current=81.8`
7. `SELECT COUNT(*) FROM sample WHERE session_id=3 AND row_no BETWEEN 5177 AND 5481 AND inv_dc_current=81.8 AND bms_current<5`
8. `SELECT COUNT(*) FROM sample_flags WHERE session_id=3 AND row_no BETWEEN 5177 AND 5481 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0`
9. `SELECT COUNT(*) FROM sample WHERE session_id=3 AND row_no BETWEEN 2751 AND 2780 AND inv_motor_speed=770 AND inv_dc_current=-0.1`
