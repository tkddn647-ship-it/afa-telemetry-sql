# 분석 에이전트 보고서: 시험1

AI가 도구를 37번 오가며 127초 동안 조사. 주장 9개 중 SQL 재실행으로 **9개 재현됨**.

## 요약

세션 '시험1'(session_id=1, 16854행)은 샘플 누락률 10.265147481631349%, 깨진 행 105개(시각 깨짐 60개), 기록 멈춤 2번, MCU 재시작 2번(row 6071, 16067)으로 품질 경고 기준을 넘는다. 부하 구간(4286행)에서 bms_current/inv_dc_current 비율의 중앙값은 0.7921146953405018이다. 품질 지표와 깨진 값 표시에 잡히지 않는 이상이 두 곳 더 있다. (1) row 12693~12992(300행): 모터는 1708~2502 rpm으로 돌고 있는데 vehicle_speed_kmh가 0.0에 고정돼 있다. 다른 구간에서는 속도/모터회전수 비율이 약 0.022233으로 일정하고, 이 300행 중 bad_speed 표시는 0개다. (2) row 9564~9863(300행): 전류 변화 없이 inv_voltage가 25 V 계단처럼 떨어졌다가(row 9563→9564: 283.6→258.6) 다시 올라온다(row 9863→9864: 251.6→276.6). 이 구간의 평균 (인버터−팩) 전압차는 −21.95 V이고, 나머지 접촉기 닫힘 구간에서는 +1.99 V다. 덧붙여, '보정 뒤 위반 비율'을 규칙 4·6대로 직접 계산하면 56.579561362575824%로, session_quality가 낸 33.3%와 맞지 않는다. 그 지표가 어떻게 정의됐는지는 도구에서 확인할 수 없었다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 10.265147481631349
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.7921146953405018

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률** 규칙 3대로 계산하면 빠진 샘플은 1928개, 누락률은 10.265147481631349%로 경고 기준 8%를 넘는다. | 10.265147481631349 | 10.265147481631349 | 재현됨 |  |
| 2 | **MCU 재시작 2번** stm_ms가 앞 행보다 작아지는 곳이 row 6071(273712→31599)과 row 16067(191279→46423) 두 군데 있다. | 2 | 2 | 재현됨 | 6071~16067 |
| 3 | **기록 멈춤 2번** 간격이 1000 ms를 넘는 멈춤이 row 7972(43960 ms)와 row 8048(1259 ms) 두 군데 있다. | 2 | 2 | 재현됨 | 7972~8048 |
| 4 | **시각(stm_ms) 깨진 행** bad_ms=1인 행이 60개 있다. | 60 | 60 | 재현됨 |  |
| 5 | **깨진 행 105개** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행이 105개로, 전체의 0.623%다. 행 손상(n_bad_cols>=3)은 0개다. | 105 | 105 | 재현됨 |  |
| 6 | **부하 구간 팩/인버터 전류비 중앙값** 부하 구간(inv_dc_current>25, bad_inv·bad_bms 제외, 4286행)에서 bms_current/inv_dc_current의 중앙값은 0.7921146953405018이다. | 0.7921146953405018 | 0.7921146953405018 | 재현됨 |  |
| 7 | **[지표 밖 이상] 모터가 도는데 차량 속도가 0에 고정** row 12693~12992의 300행에서 inv_motor_speed는 1708~2502 rpm(평균 1965.33)인데 vehicle_speed_kmh는 0.0 한 값뿐이다. 바로 앞 row 12692는 55.626 km/h, 바로 뒤 row 12993은 40.864 km/h다. 다른 주행 구간에서는 속도/회전수 비율이 약 0.022233으로 일정하다. 이 구간의 bad_speed 표시는 0개라서 품질 지표에 잡히지 않는다. 세션 전체에서 모터가 300 rpm을 넘는데 속도가 0인 행은 이 300행뿐이다. | 300 | 300 | 재현됨 | 12693~12992 |
| 8 | **[지표 밖 이상] 인버터 전압이 25 V 계단처럼 떨어진 구간** row 9564에서 inv_voltage가 전류 변화 없이 283.6→258.6 V(−25 V)로 떨어지고, row 9864에서 251.6→276.6 V(+25 V)로 돌아온다. 그 사이 bms_voltage는 277~279 V로 그대로다. row 9564~9863(300행)의 평균 (inv_voltage−bms_voltage)는 −21.95233333333333 V이고, 나머지 접촉기 닫힘 구간(row>4952)은 +1.9918720910187913 V다. 이 300행 중 깨진 값 표시가 붙은 행은 2개뿐이다. | -21.95233333333333 | -21.95233333333333 | 재현됨 | 9564~9863 |
| 9 | **보정 뒤 위반 비율 재계산값이 지표와 다름** 부하 구간(bad_inv·bad_bms 제외)에서 inv_dc_current > bms_current×(scale_correction 표의 factor)인 행의 비율을 계산하면 56.579561362575824%로, session_quality가 낸 33.3%와 다르다. 보정 전 비율도 94.6803546430238%로 지표의 93.1%와 다르다. 지표가 어떻게 정의됐는지는 도구로 확인할 수 없었다. 어느 쪽 정의로 봐도 경고 기준 30%는 넘는다. | 56.579561362575824 | 56.579561362575824 | 재현됨 |  |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) ps, LAG(row_no) OVER (ORDER BY row_no) pr FROM sample_flags WHERE session_id=1 AND bad_ms=0), d AS (SELECT row_no, pr, stm_ms-ps d FROM g WHERE ps IS NOT NULL) SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-(row_no-pr-1),0) ELSE 0 END)*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=1)+SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-(row_no-pr-1),0) ELSE 0 END)) FROM d`
2. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) ps FROM sample_flags WHERE session_id=1 AND bad_ms=0) SELECT SUM(stm_ms-ps<0) FROM g`
3. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) ps FROM sample_flags WHERE session_id=1 AND bad_ms=0) SELECT SUM(stm_ms-ps>1000) FROM g`
4. `SELECT SUM(bad_ms) FROM sample_flags WHERE session_id=1`
5. `SELECT SUM(bad_ms OR bad_inv OR bad_bms OR bad_speed OR bad_value) FROM sample_flags WHERE session_id=1`
6. `WITH r AS (SELECT bms_current*1.0/inv_dc_current x FROM sample_flags WHERE session_id=1 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT x, ROW_NUMBER() OVER (ORDER BY x) rn, COUNT(*) OVER () n FROM r) SELECT AVG(x) FROM o WHERE rn IN ((n+1)/2,(n+2)/2)`
7. `SELECT COUNT(*) FROM sample WHERE session_id=1 AND vehicle_speed_kmh=0 AND ABS(inv_motor_speed)>300`
8. `SELECT AVG(inv_voltage - bms_voltage) FROM sample WHERE session_id=1 AND row_no BETWEEN 9564 AND 9863`
9. `SELECT AVG(CASE WHEN inv_dc_current > bms_current*(SELECT factor FROM scale_correction WHERE column_name='bms_current') THEN 1.0 ELSE 0 END)*100 FROM sample_flags WHERE session_id=1 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0`
