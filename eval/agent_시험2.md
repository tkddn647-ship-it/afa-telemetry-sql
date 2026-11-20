# 분석 에이전트 보고서: 시험2

AI가 도구를 28번 오가며 93초 동안 조사. 주장 7개 중 SQL 재실행으로 **7개 재현됨**.

## 요약

세션 '시험2'(session_id=2, 32576행): 분석 규칙 v6대로 bad_ms 행을 빼고 stm_ms 간격을 계산했습니다. 빠진 샘플은 1949개, 누락률은 5.6451846488052135%입니다. 멈춘 구간은 0번, MCU 재시작은 2번(row 12093, 18233)입니다. 깨진 행은 105행(0.322%)으로 경고 기준 0.05%를 넘습니다. 부하 구간(7440행)에서 bms_current/inv_dc_current의 중앙값은 0.7934186471663619입니다. 품질 지표에는 안 잡히는 이상도 하나 찾았습니다. row 24136~24436의 301행 동안 inv_dc_current가 58.9 A에 멈춰 있었습니다. 같은 구간에서 모터 속도는 1250~1920 rpm, bms_current는 -1.9~45.7 A(서로 다른 값 21개)로 계속 바뀌었습니다. 이 구간의 bad_inv, bad_bms, bad_value 표시는 모두 0입니다. 그래서 301행이 전부 부하 구간(>25 A)으로 들어갔고, 팩/인버터 전류 비율이 평균 0.145로 떨어지는 모순 구간이 생겼습니다. 이 구간을 빼고 나면, 부하 구간에서 비율이 0.4 미만이거나 1.3 초과인 행이 10행 이상 이어지는 묶음은 14행 이하로 짧은 것뿐이었습니다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 5.6451846488052135
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.7934186471663619

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **누락률** bad_ms 행을 빼고 앞 행과의 stm_ms 간격을 계산하면 15<d<=1000 간격에서 빠진 샘플이 1949개입니다. 받은 샘플 32576개 대비 누락률은 5.6451846488052135%입니다. | 5.6451846488052135 | 5.6451846488052135 | 재현됨 |  |
| 2 | **MCU 재시작 2번** stm_ms가 거꾸로 간 곳이 2번 있습니다. row 12093에서는 264372에서 52900으로, row 18233에서는 118270에서 39266으로 바뀌었습니다. 규칙상 MCU 재시작 2번입니다. | 2 | 2 | 재현됨 | 12093~18233 |
| 3 | **깨진 행 105행** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행이 105행입니다(전체의 0.322%). 경고 기준 0.05%를 넘습니다. | 105 | 105 | 재현됨 |  |
| 4 | **부하 구간 팩/인버터 전류 비율 중앙값** 부하 구간(inv_dc_current>25, bad_inv·bad_bms 제외)은 7440행입니다. 이 구간에서 bms_current/inv_dc_current의 중앙값은 0.7934186471663619입니다. | 0.7934186471663619 | 0.7934186471663619 | 재현됨 |  |
| 5 | **인버터 DC 전류 58.9 A 고착 (지표 미검출)** row 24136~24436의 301행 동안 inv_dc_current가 58.9 A 한 값에 멈춰 있었습니다. 같은 구간에서 inv_motor_speed는 1250~1920, inv_torque_feedback은 -2.9~82.0, bms_current는 -1.9~45.7로 계속 바뀌었습니다. 이 301행은 bad_inv, bad_bms, bad_value가 모두 0이라 품질 지표에 잡히지 않았고, 전부 부하 구간(>25 A)으로 들어갔습니다. 바로 앞 행(24135)은 24.1 A, 바로 뒤 행(24437)은 28.4 A입니다. | 301 | 301 | 재현됨 | 24136~24436 |
| 6 | **고착 구간의 팩/인버터 전류 모순** 고착 구간 row 24136~24436에서 bms_current/inv_dc_current 평균은 0.14535024733627017입니다(최소 -0.032, 최대 0.776). 세션 중앙값 0.793과 크게 어긋납니다. 301행 중 208행은 인버터 전류가 58.9 A로 찍혀 있는데 팩 전류는 5 A 미만이어서 두 신호가 서로 모순됩니다. | 0.14535024733627017 | 0.14535024733627017 | 재현됨 | 24136~24436 |
| 7 | **고착 구간의 품질 플래그 미검출** row 24136~24436의 301행 가운데 bad_inv=1인 행은 0행입니다. 301행 모두 부하 구간 조건(inv_dc_current>25, bad_inv=0, bad_bms=0)을 통과해 부하 구간 7440행에 들어 있습니다. | 301 | 301 | 재현됨 | 24136~24436 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) pm, LAG(row_no) OVER (ORDER BY row_no) pr FROM sample_flags WHERE session_id=2 AND bad_ms=0), d AS (SELECT stm_ms-pm d, row_no-pr-1 nb FROM g WHERE pm IS NOT NULL), m AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) miss FROM d) SELECT miss*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=2)+miss) FROM m`
2. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) pm FROM sample_flags WHERE session_id=2 AND bad_ms=0) SELECT COUNT(*) FROM g WHERE stm_ms-pm<0`
3. `SELECT COUNT(*) FROM sample_flags WHERE session_id=2 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
4. `WITH s AS (SELECT bms_current*1.0/inv_dc_current r FROM sample_flags WHERE session_id=2 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT r, ROW_NUMBER() OVER (ORDER BY r) rn, COUNT(*) OVER () c FROM s) SELECT AVG(r) FROM o WHERE rn IN ((c+1)/2, (c+2)/2)`
5. `WITH s AS (SELECT row_no, inv_dc_current v FROM sample WHERE session_id=2), a AS (SELECT row_no, v, CASE WHEN v = LAG(v) OVER (ORDER BY row_no) THEN 0 ELSE 1 END st FROM s), b AS (SELECT row_no, v, SUM(st) OVER (ORDER BY row_no) grp FROM a) SELECT COUNT(*) n, MIN(row_no) r1, MAX(row_no) r2, v FROM b GROUP BY grp HAVING MIN(row_no)=24136`
6. `SELECT AVG(bms_current*1.0/inv_dc_current) FROM sample WHERE session_id=2 AND row_no BETWEEN 24136 AND 24436`
7. `SELECT SUM(inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), SUM(bad_inv) FROM sample_flags WHERE session_id=2 AND row_no BETWEEN 24136 AND 24436`
