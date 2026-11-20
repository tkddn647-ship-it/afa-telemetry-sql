# 분석 에이전트 보고서: 시험3

AI가 도구를 36번 오가며 141초 동안 조사. 주장 8개 중 SQL 재실행으로 **8개 재현됨**.

## 요약

시험3(24,034행)을 조사했다. session_quality 지표 4개를 SQL로 다시 계산했고 모두 같은 값이 나왔다. 누락률은 10.717337196775512%(빠진 샘플 2,885개)이고 MCU 재시작은 4번(row 3820, 11286, 19210, 23385)이다. 깨진 행은 111개이며 부하 구간의 팩/인버터 전류비 중앙값은 0.7881033759069377이다. 지표에 안 잡히는 이상은 세 가지를 찾았다. (1) row 11286의 재시작은 정차가 아니라 주행 중(차속 39.841 km/h, 인버터 전류 92.2 A)에 일어났다. (2) 재시작 4번 중 2번(row 3820, 11286)은 바로 앞 행과 ts_utc가 같아서 로거 쪽 시각에 공백이 없다. (3) 세 번째 재시작 뒤 row 19210부터 24034까지 4,825행 내내 주 접촉기가 열려 있고 inv_voltage가 0이어서, 이 구간에는 고전압 없이 기록만 남았다. 이 밖에 bms_charge는 세션 전체 24,034행이 모두 0이다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 10.717337196775512
- broken_timestamp_rows: 60
- mcu_restarts: 4
- pack_to_inverter_ratio_median: 0.7881033759069377

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률 10.7%** bad_ms 행을 빼고 stm_ms 간격으로 세면 빠진 샘플은 2,885개다. 누락률은 2885/(24034+2885)*100 = 10.717337196775512%로 경고 기준 8%를 넘는다. | 10.717337196775512 | 10.717337196775512 | 재현됨 | 1~24034 |
| 2 | **MCU 재시작 4번** bad_ms 행을 뺀 뒤 stm_ms가 앞 행보다 작아지는 곳이 4곳이다(row 3820, 11286, 19210, 23385). | 4 | 4 | 재현됨 | 3820~23385 |
| 3 | **깨진 행 111개** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행이 111개로 전체의 0.462%다. 그중 시각(bad_ms)이 깨진 행은 60개이고, 행 손상(n_bad_cols>=3)은 0개다. | 111 | 111 | 재현됨 |  |
| 4 | **팩/인버터 전류비 중앙값 0.788** 부하 구간(inv_dc_current>25 A, bad_inv·bad_bms 제외, 5,940행)에서 bms_current/inv_dc_current 원본 비율의 중앙값은 0.7881033759069377이다. | 0.7881033759069377 | 0.7881033759069377 | 재현됨 |  |
| 5 | **주행 중 MCU 재시작 (row 11286)** 재시작 지표는 횟수만 센다. 두 번째 재시작인 row 11286(stm_ms 129625에서 41834로 떨어짐) 시점의 차속은 39.841 km/h, 인버터 DC 전류는 92.2 A다. 즉 정차 중이 아니라 부하를 건 주행 중에 재시작했다. 바로 앞 row 11283~11285도 간격이 30 ms였다. | 39.841 | 39.841 | 재현됨 | 11283~11286 |
| 6 | **ts_utc 공백이 없는 재시작 2번** 재시작 4번 중 row 3820과 row 11286은 바로 앞 행과 ts_utc 값이 같다. 이 두 곳에서는 MCU 시계만 되돌아갔고 라즈베리파이 수신 시각에는 공백이 없다. 반대로 row 19210과 23385에서는 ts_utc가 각각 약 85초, 약 664초 건너뛴다. | 2 | 2 | 재현됨 | 3820~11286 |
| 7 | **재시작 뒤 고전압 꺼진 채 기록만 남은 구간 (row 19210~24034)** 세 번째 재시작(row 19210)부터 세션 끝(row 24034)까지 4,825행(세션의 약 20%) 모두 motor_main_contactor=0, inv_voltage=0이다. 바로 앞 row 19209까지는 접촉기가 닫혀 있었고(1) inv_voltage는 276.5 V였다. 이 구간에서 전류·속도가 0이 아닌 7개 행은 모두 bad_inv·bad_bms·bad_speed로 표시된 튄 값이다. | 4825 | 4825 | 재현됨 | 19210~24034 |
| 8 | **bms_charge 신호가 세션 내내 0** bms_charge는 시험3의 24,034행 모두 0이다. 시험1·시험2에서도 모든 행이 0이다. 이 신호는 기록되지 않거나 디코딩되지 않고 있다. | 24034 | 24034 | 재현됨 | 1~24034 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) pm, LAG(row_no) OVER (ORDER BY row_no) pr FROM sample_flags WHERE session_id=3 AND bad_ms=0), d AS (SELECT stm_ms-pm d, row_no-pr-1 nb FROM g WHERE pm IS NOT NULL), m AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) miss FROM d) SELECT miss*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=3)+miss) AS missing_pct, miss FROM m`
2. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) pm FROM sample_flags WHERE session_id=3 AND bad_ms=0) SELECT SUM(stm_ms<pm) AS restarts, GROUP_CONCAT(CASE WHEN stm_ms<pm THEN row_no END) FROM g`
3. `SELECT SUM(bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1), SUM(bad_ms), SUM(n_bad_cols>=3) FROM sample_flags WHERE session_id=3`
4. `WITH l AS (SELECT bms_current*1.0/inv_dc_current r FROM sample_flags WHERE session_id=3 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT r, ROW_NUMBER() OVER (ORDER BY r) k, COUNT(*) OVER () n FROM l) SELECT AVG(r), MIN(n) FROM o WHERE k IN ((n+1)/2, (n+2)/2)`
5. `SELECT vehicle_speed_kmh, inv_dc_current, row_no FROM sample WHERE session_id=3 AND row_no=11286`
6. `WITH g AS (SELECT row_no, stm_ms, ts_utc, LAG(stm_ms) OVER (ORDER BY row_no) pm, LAG(ts_utc) OVER (ORDER BY row_no) pts FROM sample_flags WHERE session_id=3 AND bad_ms=0) SELECT SUM(stm_ms<pm AND ts_utc=pts), GROUP_CONCAT(CASE WHEN stm_ms<pm AND ts_utc=pts THEN row_no END) FROM g`
7. `SELECT COUNT(*) AS rows_hv_off, MIN(row_no), MAX(row_no), SUM(inv_voltage=0), SUM(motor_main_contactor=0) FROM sample WHERE session_id=3 AND row_no BETWEEN 19210 AND 24034 AND inv_voltage=0 AND motor_main_contactor=0`
8. `SELECT SUM(bms_charge=0) AS zero_rows, COUNT(*) FROM sample WHERE session_id=3`
