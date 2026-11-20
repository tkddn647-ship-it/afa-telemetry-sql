# 분석 에이전트 보고서: 시험3

AI가 도구를 24번 오가며 106초 동안 조사. 주장 7개 중 SQL 재실행으로 **7개 재현됨**.

## 요약

세션 '시험3'(24061행)에는 품질 경고가 4개 있습니다. 누락률은 10.617%로 기준 8%를 넘고, 깨진 행은 107행(0.445%)이며, MCU가 4번 재시작했고, 보정 뒤에도 인버터 전류가 팩 전류보다 큰 행이 32.6%입니다. 시각(stm_ms)이 깨진 행은 60행이고 기록이 멈춘 구간이 1번 있습니다. 부하 구간에서 팩 전류/인버터 전류 비율의 중앙값은 0.7959입니다. 품질 지표에 잡히지 않는 이상도 하나 찾았습니다. row_no 5786~6085의 300행 동안 차량 속도(vehicle_speed_kmh)가 0.0에 멈춰 있었는데, 같은 구간에서 모터는 1115~2900 rpm으로 돌았고 인버터 DC 전류도 평균 약 87.8 A였습니다. 두 신호가 서로 모순되는데, 이 구간의 bad_speed 표시는 0건이라 기존 지표가 잡지 못했습니다. 다른 신호도 같은 값에 멈춘 구간을 살펴봤지만, 정차나 MCU 재시작 뒤 인버터가 꺼진 상태(19248행부터 끝까지, 접촉기 열림)처럼 실제 상태로 설명되는 구간이었습니다. 그래서 그 구간들은 이상으로 넣지 않았습니다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 10.617036294067388
- broken_timestamp_rows: 60
- mcu_restarts: 4
- pack_to_inverter_ratio_median: 0.79585326953748

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률 10.617%** 분석 규칙 3번으로 계산하면 빠진 샘플은 2858개이고, 누락률은 2858/(24061+2858)*100 = 10.617%로 경고 기준 8%를 넘는다. | 10.617036294067388 | 10.617036294067388 | 재현됨 |  |
| 2 | **MCU 재시작 4번** bad_ms 행을 뺀 뒤 앞 행과의 stm_ms 간격이 음수인 곳이 4번 있다. 주행 중 MCU가 4번 재시작했다는 뜻이다. | 4 | 4 | 재현됨 |  |
| 3 | **기록이 멈춘 구간 1번** stm_ms 간격이 1000 ms를 넘는 곳이 1번 있다. 이 구간은 누락으로 세지 않았다. | 1 | 1 | 재현됨 |  |
| 4 | **시각(stm_ms)이 깨진 행 60행** sample_flags에서 bad_ms=1인 행이 60행이다. | 60 | 60 | 재현됨 |  |
| 5 | **깨진 행 107행** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행이 107행이다. 전체의 0.445%로 기준 0.05%를 넘는다. | 107 | 107 | 재현됨 |  |
| 6 | **부하 구간 팩/인버터 전류 비율 중앙값 0.7959** 부하 구간(inv_dc_current>25 A, bad_inv·bad_bms 행 제외) 5964행에서 bms_current/inv_dc_current의 중앙값은 0.79585다. 스케일 계수가 빠졌다는 판단(×1.25)과 맞는 값이다. | 0.79585326953748 | 0.79585326953748 | 재현됨 |  |
| 7 | **차량 속도가 0에 멈추고 모터 회전과 모순되는 구간 (row_no 5786~6085)** row_no 5786부터 6085까지 300행 동안 vehicle_speed_kmh가 0.0에 멈춰 있다. 같은 구간에서 inv_motor_speed는 1115~2900 rpm이고 inv_dc_current는 평균 약 87.8 A로, 차가 실제로 달리고 있었다. 바로 앞 5785행의 속도는 36.239 km/h, 바로 뒤 6086행은 24.79 km/h다. 이 구간의 bad_speed 표시는 0건이라 품질 지표에 잡히지 않는다. | 300 | 300 | 재현됨 | 5786~6085 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) pm, LAG(row_no) OVER (ORDER BY row_no) pr FROM sample_flags WHERE session_id=3 AND bad_ms=0), d AS (SELECT row_no, stm_ms-pm d, row_no-pr-1 nb FROM g WHERE pm IS NOT NULL), m AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) miss FROM d) SELECT miss*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=3)+miss) FROM m`
2. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) d FROM sample_flags WHERE session_id=3 AND bad_ms=0) SELECT SUM(d<0) FROM g`
3. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) d FROM sample_flags WHERE session_id=3 AND bad_ms=0) SELECT SUM(d>1000) FROM g`
4. `SELECT COUNT(*) FROM sample_flags WHERE session_id=3 AND bad_ms=1`
5. `SELECT COUNT(*) FROM sample_flags WHERE session_id=3 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
6. `WITH r AS (SELECT bms_current*1.0/inv_dc_current x FROM sample_flags WHERE session_id=3 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT x, ROW_NUMBER() OVER (ORDER BY x) rn, COUNT(*) OVER () c FROM r) SELECT AVG(x) FROM o WHERE rn IN ((c+1)/2, (c+2)/2)`
7. `SELECT COUNT(*) FROM sample WHERE session_id=3 AND row_no BETWEEN 5786 AND 6085 AND vehicle_speed_kmh=0 AND inv_motor_speed>1000`
