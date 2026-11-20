# 분석 에이전트 보고서: 시험2

AI가 도구를 25번 오가며 105초 동안 조사. 주장 6개 중 SQL 재실행으로 **6개 재현됨**.

## 요약

세션 '시험2'(전체 32,577행)를 조사했다. 품질 지표는 SQL로 다시 계산해 모두 맞음을 확인했다: 누락률 5.642%(빠진 샘플 1,948개), 깨진 행 104개(0.319%), MCU 재시작 2번(row_no 967, 18570), 부하 구간 bms_current/inv_dc_current 비율 중앙값 0.7955. 지표에 안 잡히는 이상은 두 가지 찾았다. (1) row_no 29074~29373, 300행: 모터가 1422~1887 rpm으로 돌고 인버터 전류가 평균 28.5 A인데 차량 속도가 0.0 km/h로 찍힌다. 앞 행(29073)은 31.6 km/h, 뒤 행(29374)은 41.95 km/h이고, 이 구간 bad_speed 표시는 0개다. (2) row_no 19426~19582, 157행: 인버터 전압이 BMS 팩 전압보다 20.2~23.8 V 낮다(평균 −22.3 V). 같은 전류대(10~30 A)의 다른 행에서는 차이가 평균 +2.6 V이고 최소도 +0.2 V다. 이 구간에서 깨진 값 표시가 붙은 행은 1개뿐이다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 5.6422881969587255
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.7955182072829131

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **누락률** 규칙 3대로 bad_ms 행을 빼고 간격을 계산하면 빠진 샘플은 1,948개이고 누락률은 5.6422881969587255%다. 멈춘 구간은 0번이다. | 5.6422881969587255 | 5.6422881969587255 | 재현됨 |  |
| 2 | **깨진 행** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행은 104개(전체의 0.319%)다. 이 가운데 시각이 깨진(bad_ms) 행은 60개다. | 104 | 104 | 재현됨 |  |
| 3 | **MCU 재시작 2번** stm_ms가 뒤로 돌아간 곳이 2곳 있다. row_no 966→967에서 146662→39101 ms, 18569→18570에서 225851→56954 ms로 떨어진다. | 2 | 2 | 재현됨 | 967~18570 |
| 4 | **부하 구간 팩/인버터 전류비 중앙값** 부하 구간(inv_dc_current > 25 A, bad_inv·bad_bms 행 제외, 7,218행)에서 bms_current/inv_dc_current 비율의 중앙값은 0.7955182072829131이다. 보정 계수 1.25가 필요한 이유와 맞는다. | 0.7955182072829131 | 0.7955182072829131 | 재현됨 |  |
| 5 | **주행 중 차량 속도가 0으로 빠진 구간 (지표에 없음)** row_no 29074~29373의 300행에서 inv_motor_speed는 1422~1887 rpm이고 inv_dc_current는 평균 28.5 A인데 vehicle_speed_kmh는 모두 0.0이다. 바로 앞 행 29073은 31.615 km/h, 바로 뒤 행 29374는 41.953 km/h다. 세션 전체에서 모터 속도가 1000 rpm을 넘는데 차량 속도가 0인 행은 이 300행뿐이다. 이 구간의 bad_speed 표시는 0개라서 품질 지표에 잡히지 않는다. | 300 | 300 | 재현됨 | 29074~29373 |
| 6 | **인버터 전압이 팩 전압보다 약 22 V 낮은 구간 (지표에 없음)** row_no 19426~19582의 157행에서 inv_voltage가 bms_voltage보다 20.2~23.8 V 낮다(평균 −22.3 V). 이때 인버터 전류는 평균 15.5 A, 최대 27.1 A다. 같은 전류대(10~30 A)의 다른 3,490행에서는 차이가 평균 +2.6 V, 최소 +0.2 V다. 19583행에서 inv_voltage가 257.1 V에서 282.1 V로 한 번에 돌아온다. 이 구간에서 깨진 값 표시가 붙은 행은 1개뿐이다. 접촉기가 닫힐 때의 프리차지 구간(11578~11626)은 빼고 셌다. | 157 | 157 | 재현됨 | 19426~19582 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) pm, LAG(row_no) OVER (ORDER BY row_no) pr FROM sample_flags WHERE session_id=2 AND bad_ms=0), m AS (SELECT SUM(CASE WHEN stm_ms-pm>15 AND stm_ms-pm<=1000 THEN MAX(ROUND((stm_ms-pm)/10.0)-1-(row_no-pr-1),0) ELSE 0 END) miss FROM g) SELECT miss*100.0/(miss+(SELECT COUNT(*) FROM sample WHERE session_id=2)) FROM m`
2. `SELECT COUNT(*) FROM sample_flags WHERE session_id=2 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
3. `SELECT COUNT(*) FROM (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) d FROM sample_flags WHERE session_id=2 AND bad_ms=0) WHERE d<0`
4. `WITH r AS (SELECT bms_current*1.0/inv_dc_current x FROM sample_flags WHERE session_id=2 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT x, ROW_NUMBER() OVER (ORDER BY x) rn, COUNT(*) OVER () c FROM r) SELECT AVG(x) FROM o WHERE rn IN ((c+1)/2,(c+2)/2)`
5. `SELECT COUNT(*) FROM sample WHERE session_id=2 AND vehicle_speed_kmh=0 AND inv_motor_speed>1000`
6. `SELECT COUNT(*) FROM sample WHERE session_id=2 AND row_no>12000 AND inv_voltage>100 AND inv_voltage-bms_voltage<-20`
