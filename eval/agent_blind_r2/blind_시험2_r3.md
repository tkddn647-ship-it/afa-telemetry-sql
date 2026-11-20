# 분석 에이전트 보고서: 시험2

AI가 도구를 36번 오가며 134초 동안 조사. 주장 8개 중 SQL 재실행으로 **8개 재현됨**.

## 요약

세션 '시험2'(전체 32577행)를 조사했다. 도구로 낸 품질 지표를 SQL로 다시 계산했더니 모두 같게 나왔다. 빠진 샘플은 1948개, 누락률은 5.6422881969587255%다. 시각(stm_ms)이 깨진 행은 60행, 깨진 행 전체는 104행이다. MCU는 2번 재시작했다(row 967, row 18570). 부하 구간에서 팩 전류/인버터 전류 비율의 중앙값은 0.7955182072829131이다. 지표에 안 잡히는 이상은 세 가지를 찾았다. (1) row 29074~29373의 300행에서 모터 회전수는 1422~1887인데 차량 속도는 0 km/h로 기록됐다. 연속 300행이고 bad_speed 표시는 하나도 없다. (2) 빠진 샘플 1948개 가운데 1705개는 앞 행과 간격이 19 ms인 자리에서 나왔다. row 6부터 row 32559까지 약 20행마다 고르게 반복된다. 1695번은 바로 앞 간격이 11 ms다. 순간적인 끊김이 아니라 규칙적으로 되풀이되는 누락이다. (3) bms_charge 값이 세션 전체 32577행에서 모두 0이다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 5.6422881969587255
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.7955182072829131

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **누락률** 분석 규칙 3번으로 다시 계산했다. 빠진 샘플은 1948개, 받은 샘플은 32577개이고 누락률은 5.6422881969587255%다. session_quality 값(5.6%)과 같다. | 5.6422881969587255 | 5.6422881969587255 | 재현됨 |  |
| 2 | **시각 깨진 행** stm_ms 가 깨진 행(bad_ms=1)은 60행이다. | 60 | 60 | 재현됨 |  |
| 3 | **깨진 행 전체** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행은 104행이다(전체의 약 0.319%). | 104 | 104 | 재현됨 |  |
| 4 | **MCU 재시작 2번** bad_ms 행을 빼고 보면, 앞 행보다 stm_ms 가 작아지는 곳이 2군데 있다. row 967에서는 146662에서 39101로, row 18570에서는 225851에서 56954로 떨어진다. | 2 | 2 | 재현됨 | 967~18570 |
| 5 | **부하 구간 팩/인버터 전류비 중앙값** 부하 구간(inv_dc_current>25 A, bad_inv·bad_bms 행 제외) 7218행에서 bms_current/inv_dc_current 의 중앙값은 0.7955182072829131이다. | 0.7955182072829131 | 0.7955182072829131 | 재현됨 |  |
| 6 | **모터는 도는데 차량 속도가 0 (지표에 안 잡힘)** row 29074~29373의 300행에서 inv_motor_speed 는 1422~1887인데 vehicle_speed_kmh 는 0이다. 이 300행은 끊기지 않고 이어진다. 이 구간 앞뒤에서는 속도/모터 회전수 비율이 약 0.0222로 일정하다. 이 300행에는 bad_speed 표시가 하나도 없어서 '속도_튐' 지표(14)에 들어가지 않는다. | 300 | 300 | 재현됨 | 29074~29373 |
| 7 | **주기적인 19 ms 간격 누락 (지표에 안 잡힘)** 빠진 샘플 1948개 가운데 1705개는 앞 행과 간격이 19 ms인 자리에서 나왔다(그 사이에 bad_ms 행 없음). 이런 자리는 row 6부터 row 32559까지 약 20행마다 고르게 반복된다. 그중 1695번은 바로 앞 간격이 11 ms다. 누락률 지표는 이 누락이 규칙적으로 되풀이된다는 것을 따로 보여 주지 않는다. | 1705 | 1705 | 재현됨 | 6~32559 |
| 8 | **bms_charge 전 구간 0 (지표에 안 잡힘)** bms_charge 는 세션 전체 32577행에서 모두 0이고 다른 값이 하나도 없다. 이 열로는 충전 상태 정보를 얻을 수 없다. | 32577 | 32577 | 재현됨 | 1~32577 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, CAST(stm_ms AS REAL) ms, LAG(CAST(stm_ms AS REAL)) OVER (ORDER BY row_no) pms, LAG(row_no) OVER (ORDER BY row_no) prn FROM sample_flags WHERE session_id=2 AND bad_ms=0), m AS (SELECT ms-pms d, row_no-prn-1 nb FROM g WHERE pms IS NOT NULL), x AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) miss FROM m) SELECT miss*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=2)+miss) FROM x`
2. `SELECT COUNT(*) FROM sample_flags WHERE session_id=2 AND bad_ms=1`
3. `SELECT COUNT(*) FROM sample_flags WHERE session_id=2 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
4. `WITH g AS (SELECT row_no, CAST(stm_ms AS REAL) ms, LAG(CAST(stm_ms AS REAL)) OVER (ORDER BY row_no) pms FROM sample_flags WHERE session_id=2 AND bad_ms=0) SELECT COUNT(*), MIN(row_no), MAX(row_no) FROM g WHERE ms-pms<0`
5. `WITH l AS (SELECT bms_current*1.0/inv_dc_current r FROM sample_flags WHERE session_id=2 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT r, ROW_NUMBER() OVER (ORDER BY r) rn, COUNT(*) OVER () c FROM l) SELECT AVG(r), MAX(c) FROM o WHERE rn IN ((c+1)/2, (c+2)/2)`
6. `SELECT COUNT(*), MIN(row_no), MAX(row_no), MAX(row_no)-MIN(row_no)+1, SUM(bad_speed) FROM sample_flags WHERE session_id=2 AND vehicle_speed_kmh=0 AND inv_motor_speed>50`
7. `WITH g AS (SELECT row_no, CAST(stm_ms AS REAL) ms, LAG(CAST(stm_ms AS REAL)) OVER (ORDER BY row_no) pms, LAG(row_no) OVER (ORDER BY row_no) prn FROM sample_flags WHERE session_id=2 AND bad_ms=0) SELECT SUM(ms-pms=19 AND row_no-prn=1), MIN(CASE WHEN ms-pms=19 AND row_no-prn=1 THEN row_no END), MAX(CASE WHEN ms-pms=19 AND row_no-prn=1 THEN row_no END) FROM g`
8. `SELECT SUM(bms_charge=0), COUNT(*) FROM sample WHERE session_id=2`
