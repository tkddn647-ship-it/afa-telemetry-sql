# 분석 에이전트 보고서: 오후2차

AI가 도구를 37번 오가며 138초 동안 조사. 주장 14개 중 SQL 재실행으로 **14개 재현됨**.

## 요약

세션 '오후2차'(session_id=2, 32710행)를 조사했습니다. 경고 규칙에 걸린 항목은 없습니다. 누락률은 5.2570601013758145%로 기준 8%보다 낮습니다. 깨진 행은 row 30147 하나(bad_speed, 비율 0.003%)이고 MCU 재시작 0회, 멈춘 구간 0개입니다. 부하 구간(7249행)의 팩전류/인버터전류 비율 중앙값은 0.7953321364452423입니다. 지표에 안 잡히는 이상도 직접 찾았습니다. (1) bms_charge는 세션 전체(row 1~32710)에서 0.0, bms_ccl은 12로 멈춰 있습니다. 다른 세션 1·3·4·5·10에서는 bms_charge가 변합니다. (2) 앞뒤 행 값이 같은데 한 행만 튀는 단일 행 이상이 6개 있고, 모두 sample_flags에서 깨진 행으로 표시되지 않았습니다. 해당 행은 15063 ecu_temp 4.0(앞뒤 45.0), 16816 bms_dcl 90(앞뒤 190), 17816 bms_dcl 590(앞뒤 190), 23003 inv_temp_igt 6.8(앞뒤 36.8), 25023 bms_voltage 78.1(앞뒤 278.1), 28403 inv_temp_motor 420.0(앞뒤 42.0)입니다. (3) 신호끼리 어긋나는 구간이 두 곳 있습니다. row 20870~20985에서는 접촉기가 닫힌 상태로 BMS 전압이 인버터 전압보다 10V 넘게 높습니다(116행, 평균 차이 약 13.9V). row 16648~16657에서는 인버터 DC 전류가 25A를 넘는데 BMS 전류는 0 이하입니다(10행).

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 5.2570601013758145
- broken_timestamp_rows: 0
- mcu_restarts: 0
- pack_to_inverter_ratio_median: 0.7953321364452423

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률** 분석 규칙 3에 따라 bad_ms 행을 빼고 stm_ms 간격으로 계산하면 빠진 샘플은 1815개, 누락률은 5.2570601013758145%입니다. 경고 기준 8%보다 낮습니다. 간격이 1000ms를 넘는 멈춘 구간과 간격이 음수인 MCU 재시작은 모두 0입니다. | 5.2570601013758145 | 5.2570601013758145 | 재현됨 |  |
| 2 | **MCU 재시작 없음** bad_ms 행을 뺀 뒤 앞 행과의 stm_ms 차이가 음수인 곳이 없습니다. MCU 재시작은 0회입니다. | 0 | 0 | 재현됨 |  |
| 3 | **깨진 행 1개 (속도 튐)** 깨진 행은 row 30147 하나이고 bad_speed=1입니다. 이 행에서 vehicle_speed_kmh는 4.558, inv_motor_speed는 205로, 앞뒤 행 값(46.8, 2105)과 다릅니다. 시각이 깨진 bad_ms 행은 0개입니다. | 1 | 1 | 재현됨 | 30147~30147 |
| 4 | **부하 구간 팩/인버터 전류 비율 중앙값** 부하 구간(inv_dc_current>25A, bad_inv·bad_bms 제외, 7249행)에서 보정 전 bms_current/inv_dc_current 비율의 중앙값은 0.7953321364452423입니다. | 0.7953321364452423 | 0.7953321364452423 | 재현됨 |  |
| 5 | **bms_charge 세션 전체 0으로 멈춤** bms_charge는 row 1부터 32710까지 32710행 전부 0.0입니다. 같은 열이 세션 1·3·4·5·10에서는 여러 값을 가지므로, 이 세션에서는 BMS 충전량 신호가 기록되지 않았거나 멈춘 것으로 보입니다. | 32710 | 32710 | 재현됨 | 1~32710 |
| 6 | **bms_ccl 세션 전체 12로 멈춤** bms_ccl은 32710행 전부 12입니다. 세션 1·3·4·5·10에서는 이 열의 값이 여러 개(7~11종)입니다. | 32710 | 32710 | 재현됨 | 1~32710 |
| 7 | **ecu_temp 한 행 튐 (플래그 없음)** row 15063의 ecu_temp는 4.0입니다. 앞뒤 행은 45.0으로 같습니다. 이 행은 sample_flags에서 깨진 행으로 표시되지 않았습니다. | 4 | 4.0 | 재현됨 | 15063~15063 |
| 8 | **bms_dcl 한 행 튐 (90)** row 16816의 bms_dcl은 90입니다. 세션의 나머지 32708행은 모두 190입니다. 이 행은 깨진 행으로 표시되지 않았습니다. | 90 | 90.0 | 재현됨 | 16816~16816 |
| 9 | **bms_dcl 한 행 튐 (590)** row 17816의 bms_dcl은 590입니다. 세션의 나머지 32708행은 모두 190입니다. 이 행은 깨진 행으로 표시되지 않았습니다. | 590 | 590.0 | 재현됨 | 17816~17816 |
| 10 | **inv_temp_igt 한 행 튐 (플래그 없음)** row 23003의 inv_temp_igt는 6.8입니다. 앞뒤 행은 36.8로 같습니다. 이 행은 깨진 행으로 표시되지 않았습니다. | 6.8 | 6.8 | 재현됨 | 23003~23003 |
| 11 | **bms_voltage 한 행 튐 (플래그 없음)** row 25023의 bms_voltage는 78.1입니다. 앞뒤 행은 278.1로 같고, 같은 행의 inv_voltage는 280.6입니다. 이 행은 bad_bms를 포함해 어떤 깨진 행 표시도 없습니다. | 78.1 | 78.1 | 재현됨 | 25023~25023 |
| 12 | **inv_temp_motor 한 행 튐 (플래그 없음)** row 28403의 inv_temp_motor는 420.0입니다. 앞뒤 행은 42.0으로 같습니다. 이 행은 깨진 행으로 표시되지 않았습니다. | 420 | 420.0 | 재현됨 | 28403~28403 |
| 13 | **BMS 전압과 인버터 전압 불일치 구간** row 20870~20985의 116행에서 주 접촉기가 닫혀 있는데(motor_main_contactor=1) bms_voltage가 inv_voltage보다 10V 넘게 높습니다. 평균 차이는 13.906V이고, 이 구간의 평균 inv_dc_current는 약 138.7A입니다. 이보다 짧은 같은 종류의 구간도 있습니다(20820~20858 39행, 29596~29614 19행, 29644~29682 39행). | 116 | 116 | 재현됨 | 20870~20985 |
| 14 | **부하인데 BMS 전류 0 이하인 구간** row 16648~16657의 10행 연속에서 inv_dc_current는 25A를 넘는데(최소 28.6A) bms_current는 0 이하(최대 0.0)입니다. 두 전류 신호가 서로 맞지 않습니다. 세션 전체에서 이런 행은 40개이고, 그중 가장 긴 연속 구간이 이곳입니다. | 10 | 10 | 재현됨 | 16648~16657 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) pm, LAG(row_no) OVER (ORDER BY row_no) pr FROM sample_flags WHERE session_id=2 AND bad_ms=0), d AS (SELECT stm_ms-pm d, row_no-pr-1 nb FROM g WHERE pm IS NOT NULL), m AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) miss FROM d) SELECT miss*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=2)+miss) FROM m`
2. `WITH g AS (SELECT stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) d FROM sample_flags WHERE session_id=2 AND bad_ms=0) SELECT SUM(CASE WHEN d<0 THEN 1 ELSE 0 END) FROM g`
3. `SELECT COUNT(*) FROM sample_flags WHERE session_id=2 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1)`
4. `WITH r AS (SELECT bms_current*1.0/inv_dc_current x FROM sample_flags WHERE session_id=2 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT x, ROW_NUMBER() OVER (ORDER BY x) rn, COUNT(*) OVER () c FROM r) SELECT AVG(x) FROM o WHERE rn IN ((c+1)/2, (c+2)/2)`
5. `SELECT COUNT(*) FROM sample WHERE session_id=2 AND bms_charge=0`
6. `SELECT COUNT(*) FROM sample WHERE session_id=2 AND bms_ccl=12`
7. `SELECT ecu_temp FROM sample WHERE session_id=2 AND row_no=15063`
8. `SELECT bms_dcl FROM sample WHERE session_id=2 AND row_no=16816`
9. `SELECT bms_dcl FROM sample WHERE session_id=2 AND row_no=17816`
10. `SELECT inv_temp_igt FROM sample WHERE session_id=2 AND row_no=23003`
11. `SELECT bms_voltage FROM sample WHERE session_id=2 AND row_no=25023`
12. `SELECT inv_temp_motor FROM sample WHERE session_id=2 AND row_no=28403`
13. `SELECT COUNT(*) FROM sample WHERE session_id=2 AND row_no BETWEEN 20870 AND 20985 AND motor_main_contactor=1 AND bms_voltage-inv_voltage>10`
14. `SELECT COUNT(*) FROM sample WHERE session_id=2 AND row_no BETWEEN 16648 AND 16657 AND inv_dc_current>25 AND bms_current<=0`
