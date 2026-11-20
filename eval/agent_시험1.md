# 분석 에이전트 보고서: 시험1

AI가 도구를 28번 오가며 155초 동안 조사. 주장 7개 중 SQL 재실행으로 **7개 재현됨**.

## 요약

세션 '시험1'(16869행)의 품질을 분석 규칙 v6에 따라 다시 계산했다. 누락률 10.185283782344799%(빠진 샘플 1913개)로 경고 기준 8%를 넘는다. 깨진 행은 104개(0.617%)이고, MCU 재시작 2번(5174행, 16014행)과 기록이 멈춘 구간 2번(8066행, 8142행)이 있다. 부하 구간(4334행)에서 bms_current/inv_dc_current 비율의 중앙값은 0.8028419182948491이다. 품질 지표에는 안 잡히는 이상도 하나 찾았다. 9829~10136행(308행) 동안 inv_dc_current가 33.4 A에 그대로 멈춰 있는데, 같은 구간에서 bms_current(30가지 값), 모터 회전수(31가지), 토크 피드백(29가지)은 계속 변한다. 주행 중(회전수 300 초과) 다른 inv_dc_current 평탄 구간은 가장 길어야 48행이다. 이 구간 308행에는 bad_inv, bad_bms, bad_value 표시가 하나도 없다. 그래서 308행 모두 부하 구간(>25 A)으로 들어가 비율 계산에 섞인다. 같은 구간 안 9882~10028행 사이에서는 85행이 bms_current < 0(최저 -2.1 A, 회생/방전 없음)인데 inv_dc_current는 33.4 A로 남아 있어, 두 전류 신호가 서로 모순된다. 0~약 4930행은 메인 컨택터가 0이고 회전수와 속도가 0인 정차 상태라서, 그 구간의 긴 상수 값은 이상으로 보지 않았다. inv_voltage와 모터 회전수가 약 30행 단위로 평탄한 것은 세션 전체에 걸쳐 반복되는 갱신 주기 패턴이라 이상으로 넣지 않았다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 10.185283782344799
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.8028419182948491

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률 8% 초과** bad_ms 행을 빼고 row_no 순서로 stm_ms 간격을 계산했다. 빠진 샘플은 1913개, 누락률은 10.185283782344799%로 경고 기준 8%를 넘는다. | 10.185283782344799 | 10.185283782344799 | 재현됨 |  |
| 2 | **깨진 행 104개** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행이 104개다. 전체 16869행의 0.617%로 경고 기준 0.05%를 넘는다. | 104 | 104 | 재현됨 |  |
| 3 | **MCU 재시작 2번** stm_ms가 뒤로 간 곳이 두 군데 있다. 5173→5174행(263172→54582 ms)과 16013→16014행(223892→38924 ms)이다. | 2 | 2 | 재현됨 | 5174~16014 |
| 4 | **기록이 멈춘 구간 2번** 앞 행과의 간격이 1000 ms를 넘는 곳이 두 군데 있다. 8065→8066행(43960 ms)과 8141→8142행(1259 ms)이다. | 2 | 2 | 재현됨 | 8066~8142 |
| 5 | **팩/인버터 전류 비율 중앙값** 부하 구간(inv_dc_current > 25 A, bad_inv와 bad_bms 행 제외, 4334행)에서 보정 전 bms_current/inv_dc_current 비율의 중앙값은 0.8028419182948491이다. | 0.8028419182948491 | 0.8028419182948491 | 재현됨 |  |
| 6 | **인버터 DC 전류가 33.4 A에 멈춤 (지표 미검출)** 9829~10136행, 308행 연속으로 inv_dc_current가 33.4 A 한 값만 나온다. 같은 행들에서 bms_current는 30가지, inv_motor_speed(1727~2357 rpm)는 31가지, inv_torque_feedback은 29가지 값으로 계속 변한다. 주행 중 다른 inv_dc_current 평탄 구간은 가장 길어야 48행이다. 이 구간에는 bad_inv, bad_bms, bad_value 표시가 하나도 없어서 308행 모두 부하 구간 계산에 들어간다. | 308 | 308 | 재현됨 | 9829~10136 |
| 7 | **팩 전류 음수인데 인버터 전류 33.4 A (신호 모순)** 멈춘 구간 안의 9882~10028행 사이에서 85행은 bms_current가 0보다 작다(최저 -2.1 A). 그런데 inv_dc_current는 33.4 A 부하로 찍혀 있어 두 전류 신호가 서로 맞지 않는다. | 85 | 85 | 재현됨 | 9882~10028 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms FROM sample_flags WHERE session_id=1 AND bad_ms=0), d AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) AS d, row_no - LAG(row_no) OVER (ORDER BY row_no) - 1 AS nb FROM g) SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END)*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=1)+SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END)) AS missing_pct FROM d`
2. `SELECT COUNT(*) FROM sample_flags WHERE session_id=1 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
3. `WITH g AS (SELECT row_no, stm_ms FROM sample_flags WHERE session_id=1 AND bad_ms=0), d AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) AS d FROM g) SELECT SUM(d<0) AS restarts FROM d`
4. `WITH g AS (SELECT row_no, stm_ms FROM sample_flags WHERE session_id=1 AND bad_ms=0), d AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) AS d FROM g) SELECT SUM(d>1000) AS stalls FROM d`
5. `WITH r AS (SELECT bms_current*1.0/inv_dc_current AS x FROM sample_flags WHERE session_id=1 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT x, ROW_NUMBER() OVER (ORDER BY x) rn, COUNT(*) OVER () n FROM r) SELECT AVG(x) AS median_ratio FROM o WHERE rn IN ((n+1)/2, (n+2)/2)`
6. `SELECT COUNT(*) AS n_rows, COUNT(DISTINCT inv_dc_current), COUNT(DISTINCT bms_current), COUNT(DISTINCT inv_motor_speed), COUNT(DISTINCT inv_torque_feedback) FROM sample WHERE session_id=1 AND row_no BETWEEN 9829 AND 10136 AND inv_dc_current=33.4`
7. `SELECT COUNT(*) AS n_neg, MIN(row_no), MAX(row_no), MIN(bms_current) FROM sample WHERE session_id=1 AND row_no BETWEEN 9829 AND 10136 AND inv_dc_current=33.4 AND bms_current<0`
