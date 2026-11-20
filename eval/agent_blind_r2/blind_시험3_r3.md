# 분석 에이전트 보고서: 시험3

AI가 도구를 23번 오가며 97초 동안 조사. 주장 6개 중 SQL 재실행으로 **6개 재현됨**.

## 요약

시험3(24034행)의 품질 지표는 SQL로 다시 계산해 모두 맞음을 확인했다. 누락률 10.717337196775512%(빠진 샘플 2885개), 깨진 행 111개(그중 시각 깨짐 60개), MCU 재시작 4번, 멈춘 구간 1번이다. 부하 구간에서 팩 전류/인버터 전류 비율의 중앙값은 0.7881033759069377이다. 지표에 안 잡히는 이상도 하나 찾았다. row_no 19210에서 MCU가 재시작한 뒤(stm_ms 132964→38898) 세션 끝인 row_no 24034까지 4825행 동안 인버터 신호 네 개가 모두 0.0으로 고정된다. 네 신호는 inv_voltage, inv_motor_speed, inv_temp_igt, inv_temp_motor다. 바로 앞 행(19209)에서는 IGBT 온도 37.2, 모터 온도 45.6이었고, BMS 팩 전압은 이 구간에도 약 271~273 V로 계속 기록된다. 온도가 갑자기 정확히 0.0이 되는 것은 물리적으로 맞지 않는다. 그런데도 이 4825행 중 깨진 행 표시가 붙은 행은 22개뿐이라 깨진 행 지표에는 거의 반영되지 않는다. 인버터 쪽 데이터가 실제 값이 아니라 0으로 채워졌을 가능성이 있으며, 원인(인버터 전원 차단, CAN 수신 끊김 등)은 이 데이터만으로는 확인하지 못했다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 10.717337196775512
- broken_timestamp_rows: 60
- mcu_restarts: 4
- pack_to_inverter_ratio_median: 0.7881033759069377

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률** 분석 규칙 3번으로 계산한 시험3의 누락률은 10.717337196775512%이다. 빠진 샘플은 2885개, 받은 샘플은 24034개로, 경고 기준인 8%를 넘는다. | 10.717337196775512 | 10.717337196775512 | 재현됨 |  |
| 2 | **깨진 행 수** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 깨진 행은 111개이다. 세션 전체의 0.462%로 경고 기준인 0.05%를 넘는다. | 111 | 111 | 재현됨 |  |
| 3 | **시각(stm_ms) 깨진 행** stm_ms 값이 깨진 bad_ms 행은 60개이다. | 60 | 60 | 재현됨 |  |
| 4 | **MCU 재시작 횟수** bad_ms 행을 뺀 뒤 앞 행보다 stm_ms가 줄어든 곳, 즉 MCU 재시작은 4번이다. 위치는 row_no 3820, 11286, 19210, 23385이다. | 4 | 4 | 재현됨 |  |
| 5 | **부하 구간 팩/인버터 전류 비율 중앙값** 부하 구간(inv_dc_current > 25 A, bad_inv와 bad_bms 행 제외, 5940행)에서 보정 전 bms_current/inv_dc_current 비율의 중앙값은 0.7881033759069377이다. | 0.7881033759069377 | 0.7881033759069377 | 재현됨 |  |
| 6 | **MCU 재시작 뒤 인버터 신호 0 고정 구간 (지표 밖 이상)** row_no 19210부터 24034(세션 끝)까지 4825행 동안 inv_voltage, inv_motor_speed, inv_temp_igt, inv_temp_motor가 모두 0.0이다. 시작점 19210은 MCU 재시작 지점(stm_ms 132964→38898)과 같다. 바로 앞 행에서 IGBT 온도는 37.2, 모터 온도는 45.6이었고, inv_temp_igt=0인 행은 이 구간 말고는 없다. BMS 팩 전압은 같은 구간에서 약 271~273 V로 계속 기록된다. 이 4825행 중 깨진 행 표시가 붙은 행은 22개뿐이어서 품질 지표에는 거의 잡히지 않는다. | 4825 | 4825 | 재현됨 | 19210~24034 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) AS ps, LAG(row_no) OVER (ORDER BY row_no) AS pr FROM sample_flags WHERE session_id=3 AND bad_ms=0), m AS (SELECT SUM(CASE WHEN stm_ms-ps>15 AND stm_ms-ps<=1000 THEN MAX(ROUND((stm_ms-ps)/10.0)-1-(row_no-pr-1),0) ELSE 0 END) AS miss FROM g) SELECT miss*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=3)+miss) AS pct, miss FROM m`
2. `SELECT COUNT(*) AS broken FROM sample_flags WHERE session_id=3 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
3. `SELECT COUNT(*) FROM sample_flags WHERE session_id=3 AND bad_ms=1`
4. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) AS ps FROM sample_flags WHERE session_id=3 AND bad_ms=0) SELECT SUM(stm_ms-ps<0) AS restarts FROM g`
5. `WITH r AS (SELECT bms_current*1.0/inv_dc_current AS x FROM sample_flags WHERE session_id=3 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT x, ROW_NUMBER() OVER (ORDER BY x) rn, COUNT(*) OVER () c FROM r) SELECT AVG(x) AS median FROM o WHERE rn IN ((c+1)/2,(c+2)/2)`
6. `SELECT COUNT(*) AS n_rows, MIN(row_no) AS first_row, MAX(row_no) AS last_row, SUM(bad_ms+bad_inv+bad_bms+bad_speed+bad_value>0) AS flagged FROM sample_flags WHERE session_id=3 AND inv_voltage=0 AND inv_motor_speed=0 AND inv_temp_igt=0 AND inv_temp_motor=0`
