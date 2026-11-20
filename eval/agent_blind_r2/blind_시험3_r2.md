# 분석 에이전트 보고서: 시험3

AI가 도구를 32번 오가며 157초 동안 조사. 주장 7개 중 SQL 재실행으로 **7개 재현됨**.

## 요약

시험3(24,034행)의 품질 지표 가운데 누락률, 깨진 행, MCU 재시작, 부하 구간 전류 비율 중앙값은 분석 규칙대로 SQL로 다시 계산해 같은 값이 나왔다. 누락률은 10.717337…%, 깨진 행은 111행(0.4618457…%), MCU 재시작은 4번, bms/inv 전류 비율 중앙값은 0.7881033…이다. 보정 전·후 위반 비율(90.0%, 38.8%)은 정의가 문서에 없다. 그래서 inv_dc_current > bms_current×factor 로 직접 세어 보았지만 92.02%와 57.73%가 나와 재현하지 못했고, 결과 목록에서 뺐다. 지표에 안 잡히는 이상은 세 가지다. (1) row 19210~24034(4,825행, 세션의 약 20%)에서 인버터 신호가 모두 0이다. 인버터 전압·모터 온도·IGBT 온도·모터 회전수가 0이고 주 접촉기도 열려 있는데, BMS 전압(271~273 V)은 계속 기록된다. (2) MCU 재시작으로만 세어진 row 19210과 23385에서 ts_utc가 각각 85.1초, 663.9초 건너뛴다. 합치면 약 749초가 기록되지 않았는데, '멈춘 구간' 지표에는 1번(row 557)만 잡힌다. (3) 나머지 재시작 2번(row 3820, 11286)은 ts_utc 간격이 0초이고 신호도 끊기지 않았다. 특히 row 11286은 39.8 km/h, 인버터 전류 92.2 A로 달리는 중이다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 10.717337196775512
- broken_timestamp_rows: 60
- mcu_restarts: 4
- pack_to_inverter_ratio_median: 0.7881033759069377

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률 10.72%** 규칙 3대로 bad_ms 행을 빼고 stm_ms 간격을 계산하면 빠진 샘플은 2,885개이고 누락률은 10.717337196775512%다. 경고 기준 8%를 넘는다. | 10.717337196775512 | 10.717337196775512 | 재현됨 | 1~24034 |
| 2 | **깨진 행 111행** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행은 111행이다. 세션 전체 대비 0.4618457185653657%로 경고 기준 0.05%를 넘는다. | 111 | 111 | 재현됨 |  |
| 3 | **MCU 재시작 4번** bad_ms 행을 빼고 보면 stm_ms가 앞 행보다 작아지는 곳이 4번 있다. 위치는 row 3820, 11286, 19210, 23385다. | 4 | 4 | 재현됨 | 3820~23385 |
| 4 | **부하 구간 팩/인버터 전류 비율 중앙값 0.788** 부하 구간(inv_dc_current > 25 A, bad_inv·bad_bms 제외, 5,940행)에서 bms_current/inv_dc_current 중앙값은 0.7881033759069377이다. | 0.7881033759069377 | 0.7881033759069377 | 재현됨 |  |
| 5 | **세션 마지막 4,825행은 인버터 신호가 모두 0** row 19210부터 24034까지 4,825행 전부에서 inv_voltage, inv_temp_motor, inv_temp_igt, inv_motor_speed가 0이고 motor_main_contactor도 0이다. 같은 구간에서 bms_voltage는 271~273 V로 계속 기록된다. 바로 앞 row 19209는 inv_voltage 276.5 V, 모터 온도 45.6이고 접촉기가 닫혀 있었다. 이 구간은 품질 지표에 따로 잡히지 않지만 '전체 행' 분모에는 들어간다. | 4825 | 4825 | 재현됨 | 19210~24034 |
| 6 | **재시작에 가려진 기록 공백 약 749초** ts_utc 기준으로 앞 행과 60초 넘게 벌어진 곳은 row 19210(85.1초)과 row 23385(663.9초) 두 곳이고, 합치면 748.98초다. 두 곳 다 stm_ms가 거꾸로 가서 MCU 재시작으로만 세어졌고, '멈춘_구간' 지표(1번, row 557의 4.66초)에는 들어가지 않았다. | 748.9809706807137 | 748.9809706807137 | 재현됨 | 19210~23385 |
| 7 | **시간 공백 없는 재시작 2번** 재시작 4번 중 row 3820과 row 11286의 2번은 ts_utc 간격이 0초다. 앞 행과 같은 묶음 시각이고 신호도 이어진다. row 11286은 차량 속도 39.841 km/h, inv_dc_current 92.2 A, 접촉기가 닫힌 주행 중이었고, stm_ms만 129625에서 41834로 되돌아갔다. | 2 | 2 | 재현됨 | 3820~11286 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) d, row_no - LAG(row_no) OVER (ORDER BY row_no) - 1 nb FROM sample_flags WHERE session_id=3 AND bad_ms=0), m AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) miss FROM g), n AS (SELECT COUNT(*) c FROM sample WHERE session_id=3) SELECT miss*100.0/(c+miss) pct, miss, c FROM m,n`
2. `SELECT COUNT(*), COUNT(*)*100.0/(SELECT COUNT(*) FROM sample WHERE session_id=3) FROM sample_flags WHERE session_id=3 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
3. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) d FROM sample_flags WHERE session_id=3 AND bad_ms=0) SELECT SUM(d<0) FROM g`
4. `WITH r AS (SELECT bms_current/inv_dc_current x, ROW_NUMBER() OVER (ORDER BY bms_current/inv_dc_current) k, COUNT(*) OVER () n FROM sample_flags WHERE session_id=3 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0) SELECT AVG(x), MAX(n) FROM r WHERE k IN ((n+1)/2, (n+2)/2)`
5. `SELECT COUNT(*), MIN(row_no), MAX(row_no), SUM(inv_voltage=0 AND inv_temp_motor=0 AND inv_temp_igt=0 AND inv_motor_speed=0 AND motor_main_contactor=0) FROM sample WHERE session_id=3 AND row_no>=19210`
6. `WITH t AS (SELECT row_no, julianday(SUBSTR(ts_utc,1,4)||'-'||SUBSTR(ts_utc,6,2)||'-'||SUBSTR(ts_utc,9,2)||SUBSTR(ts_utc,11)) j FROM sample WHERE session_id=3), u AS (SELECT row_no, (j - LAG(j) OVER (ORDER BY row_no))*86400.0 dt FROM t) SELECT SUM(dt) FROM u WHERE dt > 60`
7. `WITH t AS (SELECT row_no, stm_ms, julianday(SUBSTR(ts_utc,1,4)||'-'||SUBSTR(ts_utc,6,2)||'-'||SUBSTR(ts_utc,9,2)||SUBSTR(ts_utc,11)) j FROM sample_flags WHERE session_id=3 AND bad_ms=0), u AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) d, (j - LAG(j) OVER (ORDER BY row_no))*86400.0 dt FROM t) SELECT SUM(dt < 1), SUM(dt > 60), GROUP_CONCAT(row_no||':'||dt) FROM u WHERE d < 0`
