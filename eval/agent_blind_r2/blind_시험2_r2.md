# 분석 에이전트 보고서: 시험2

AI가 도구를 27번 오가며 104초 동안 조사. 주장 7개 중 SQL 재실행으로 **7개 재현됨**.

## 요약

세션 '시험2'(32,577행)의 품질 지표를 규칙 v6에 따라 다시 계산했고, 지표 값과 모두 일치했다. 누락률은 5.6422881969587255%(빠진 샘플 1,948개)이고, 깨진 시각(bad_ms) 행은 60개다. MCU 재시작은 2번으로 row 967과 row 18570에서 일어났고, 멈춘 구간은 없다. 부하 구간(7,218행)에서 bms_current/inv_dc_current 비율의 중앙값은 0.7955182072829131이다. 지표에 잡히지 않는 이상은 두 가지를 찾았다. (1) row 30009~30316(308행)에서 inv_dc_current가 71.4 A로 고정돼 있다. 같은 구간에서 bms_current는 26.5~58.2 A, 모터 회전수는 2105~2738 rpm으로 계속 변하는데 bad_inv 표시는 0이다. 이 행들은 부하 구간 비율 계산에도 들어가며, 이 구간의 비율은 0.371~0.815로 흔들린다. (2) row 29074~29373(300행)에서 모터 회전수가 1422~1887 rpm인데도 vehicle_speed_kmh가 0이다. 바로 앞 구간은 26.8~31.6 km/h, 바로 뒤 구간은 42.0~58.0 km/h이고, bad_speed와 value_flag 표시는 없다. 덧붙여 bms_charge는 세션 전체 32,577행이 모두 0이며, 시험1과 시험3도 모든 행이 0이다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 5.6422881969587255
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.7955182072829131

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률** bad_ms 행을 빼고 stm_ms 간격으로 센 빠진 샘플은 1,948개다. 누락률은 1948/(32577+1948)×100 = 5.6422881969587255%다. | 5.6422881969587255 | 5.6422881969587255 | 재현됨 |  |
| 2 | **깨진 시각(stm_ms) 행** sample_flags에서 bad_ms=1인 행이 60개다. | 60 | 60 | 재현됨 |  |
| 3 | **MCU 재시작 2번** bad_ms 행을 뺀 뒤 stm_ms가 뒤로 돌아간 곳이 2번 있다. row 967에서는 146662에서 39101로, row 18570에서는 225851에서 56954로 돌아갔다. | 2 | 2 | 재현됨 | 967~18570 |
| 4 | **부하 구간 팩/인버터 전류비 중앙값** 부하 구간(inv_dc_current>25 A, bad_inv=0, bad_bms=0) 7,218행에서 보정 전 bms_current/inv_dc_current의 중앙값은 0.7955182072829131이다. | 0.7955182072829131 | 0.7955182072829131 | 재현됨 |  |
| 5 | **인버터 DC 전류 71.4 A 고정 (지표 미검출)** row 30009~30316의 308행에서 inv_dc_current가 71.4 A 한 값으로 고정돼 있다. 바로 앞 row 30008은 65.8 A, 바로 뒤 row 30317은 38.9 A다. 같은 구간에서 bms_current는 26.5~58.2 A(서로 다른 값 31개), 모터 회전수는 2105~2738 rpm으로 변한다. 그런데도 bad_inv는 0이어서 부하 구간 계산에 그대로 들어가고, 이 구간의 bms/inv 비율은 0.371~0.815로 흔들린다. | 308 | 308 | 재현됨 | 30009~30316 |
| 6 | **모터 회전 중 차량 속도 0 (지표 미검출)** row 29074~29373의 300행에서 inv_motor_speed는 1422~1887 rpm인데 vehicle_speed_kmh는 0이다. 바로 앞 100행은 26.8~31.6 km/h, 바로 뒤 100행은 42.0~58.0 km/h다. 이 구간에는 bad_speed와 value_flag 표시가 없다. 세션 전체에서 모터 회전수가 300 rpm을 넘는데 속도가 0인 행은 이 300행뿐이다. | 300 | 300 | 재현됨 | 29074~29373 |
| 7 | **bms_charge 전 구간 0** bms_charge는 시험2의 32,577행이 모두 0이다(최소와 최대가 모두 0). 시험1과 시험3도 모든 행이 0이라 이 신호에는 기록된 값이 없다. | 32577 | 32577 | 재현됨 | 1~32577 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) AS pm, LAG(row_no) OVER (ORDER BY row_no) AS pr FROM sample_flags WHERE session_id=2 AND bad_ms=0), d AS (SELECT row_no, pr, stm_ms-pm AS d FROM g WHERE pm IS NOT NULL), m AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-(row_no-pr-1),0) ELSE 0 END) AS miss FROM d) SELECT miss*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=2)+miss) FROM m`
2. `SELECT COUNT(*) FROM sample_flags WHERE session_id=2 AND bad_ms=1`
3. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) AS d FROM sample_flags WHERE session_id=2 AND bad_ms=0) SELECT COUNT(*), MIN(row_no), MAX(row_no) FROM g WHERE d<0`
4. `WITH x AS (SELECT bms_current*1.0/inv_dc_current AS r FROM sample_flags WHERE session_id=2 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT r, ROW_NUMBER() OVER (ORDER BY r) rn, COUNT(*) OVER () c FROM x) SELECT AVG(r) FROM o WHERE rn IN ((c+1)/2,(c+2)/2)`
5. `SELECT COUNT(*), MIN(row_no), MAX(row_no) FROM sample WHERE session_id=2 AND row_no BETWEEN 30009 AND 30316 AND inv_dc_current=71.4`
6. `SELECT COUNT(*), MIN(row_no), MAX(row_no) FROM sample WHERE session_id=2 AND inv_motor_speed>300 AND vehicle_speed_kmh=0`
7. `SELECT SUM(bms_charge=0), COUNT(*) FROM sample WHERE session_id=2`
