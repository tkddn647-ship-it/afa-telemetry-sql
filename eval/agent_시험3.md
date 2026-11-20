# 분석 에이전트 보고서: 시험3

AI가 도구를 34번 오가며 128초 동안 조사. 주장 8개 중 SQL 재실행으로 **8개 재현됨**.

## 요약

세션 '시험3'(24186행)을 분석 규칙 v4로 다시 계산한 결과, 품질 지표 값은 도구 결과와 맞았다. 다만 누락률은 반올림하지 않은 값이 10.156017830609212%다(도구는 10.2로 표시). 빠진 샘플은 2734개이고, 깨진 시각 행 60개를 빼지 않는 옛 정의로 세면 2794개가 된다. 깨진 행은 83개, 기록이 멈춘 구간은 1번(row 557), MCU 재시작은 3번(row 17790, 19367, 23522)이다. 부하 구간에서 bms_current/inv_dc_current 비율의 중앙값은 0.7959151405158664다. 지표에 안 잡히는 이상도 두 가지 찾았다. 첫째, row 11979~12279(301행) 동안 인버터 DC 전류(inv_dc_current)가 44.1 A에 그대로 멈춰 있었다. 같은 구간에서 팩 전류는 -2.1~96.3 A, 토크 피드백은 -4.6~133.8, 모터 속도는 1592~2089로 계속 움직였고, bad_inv 플래그는 하나도 서지 않았다. 둘째, 같은 구간 안 130행에서는 인버터가 44.1 A를 끌어간다고 나오는데 팩 전류는 0 이하여서 두 신호가 서로 모순된다. 이 301행은 모두 부하 구간(>25 A) 판정에 들어가므로 부하 비율과 보정 위반 지표를 오염시킨다. 그 밖에 row 19367~24186에서 깨지지 않은 행 4810개가 음수 stm_ms(-1085302~-1041355)를 가진다. 이 구간에서는 메인 컨택터와 인버터 모드가 0이고 인버터 전압과 모터 속도도 0이어서, 신호끼리는 서로 맞는다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 10.156017830609212
- broken_timestamp_rows: 60
- mcu_restarts: 3
- pack_to_inverter_ratio_median: 0.7959151405158664

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **누락률 (규칙 v4 재계산)** 시험3에서 깨진 시각 행을 받은 샘플로 세고 두 행 사이의 bad_ms 행 수를 빼서 다시 계산하면, 빠진 샘플은 2734개이고 누락률은 10.156017830609212%다. 경고 기준인 8%를 넘는다. | 10.156017830609212 | 10.156017830609212 | 재현됨 |  |
| 2 | **깨진 행 수** 시험3에서 bad_ms, bad_inv, bad_bms, bad_speed 중 하나라도 1인 행은 83개다. 그중 시각이 깨진 행(bad_ms)은 60개다. | 83 | 83 | 재현됨 |  |
| 3 | **MCU 재시작 3회** bad_ms 행을 빼고 앞 행과의 stm_ms 간격이 음수인 곳은 row 17790, 19367, 23522의 세 곳이다. 그중 19367과 23522에서는 시계가 -1085296, -1085302처럼 음수 값에서 다시 시작한다. | 3 | 3 | 재현됨 | 17790~23522 |
| 4 | **기록 멈춤 1회** row 557에서 앞 행과의 stm_ms 간격이 4659 ms로 1000 ms를 넘는다. 기록이 멈춘 구간 1번으로 보고, 누락으로는 세지 않았다. | 1 | 1 | 재현됨 | 557~557 |
| 5 | **부하 구간 팩/인버터 전류 비율 중앙값** 부하 구간(inv_dc_current>25 A, bad_inv·bad_bms 제외, 6222행)에서 보정 전 bms_current/inv_dc_current의 중앙값은 0.7959151405158664다. | 0.7959151405158664 | 0.7959151405158664 | 재현됨 |  |
| 6 | **인버터 DC 전류 44.1 A 고착 (지표 미검출)** row 11979~12279의 301행 연속으로 inv_dc_current가 정확히 44.1 A로 바뀌지 않는다. 같은 구간에서 bms_current는 -2.1~96.3 A, inv_torque_feedback은 -4.6~133.8로 변하고, 구간 바로 다음 행(12280)에서 122.6 A로 뛴다. bad_inv 플래그는 구간 전체에서 0이다. | 301 | 301 | 재현됨 | 11979~12279 |
| 7 | **고착 구간의 인버터·팩 전류 모순** 고착 구간 row 11979~12279의 301행 가운데 130행은 인버터 DC 전류가 44.1 A(부하 판정 >25 A)인데 팩 전류가 0 이하다. 두 신호가 서로 모순된다. 같은 구간에서 토크 피드백이 0 이하인 행도 69행이다. | 130 | 130 | 재현됨 | 11979~12279 |
| 8 | **재시작 뒤 음수 MCU 시계** row 19367~24186에서 bad_ms=0인 행 4810개가 모두 음수 stm_ms(-1085302~-1041355)를 가진다. 이 구간은 메인 컨택터·인버터 모드가 0이고 인버터 전압·모터 속도도 0이라 신호끼리는 서로 맞는다. | 4810 | 4810 | 재현됨 | 19367~24186 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) AS d, row_no - LAG(row_no) OVER (ORDER BY row_no) - 1 AS nb FROM sample_flags WHERE session_id=3 AND bad_ms=0), m AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) miss FROM g) SELECT 100.0*miss/((SELECT COUNT(*) FROM sample WHERE session_id=3)+miss) AS missing_rate_pct, (SELECT label FROM session WHERE session_id=3) FROM m`
2. `SELECT COUNT(*) AS broken_rows, (SELECT label FROM session WHERE session_id=3) FROM sample_flags WHERE session_id=3 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1)`
3. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) AS d FROM sample_flags WHERE session_id=3 AND bad_ms=0) SELECT SUM(d<0) AS restarts, MIN(CASE WHEN d<0 THEN row_no END), MAX(CASE WHEN d<0 THEN row_no END) FROM g`
4. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) AS d FROM sample_flags WHERE session_id=3 AND bad_ms=0) SELECT SUM(d>1000) AS stalls, MIN(CASE WHEN d>1000 THEN row_no END) FROM g`
5. `WITH x AS (SELECT bms_current*1.0/inv_dc_current r FROM sample_flags WHERE session_id=3 AND bad_inv=0 AND bad_bms=0 AND inv_dc_current>25 ORDER BY r), n AS (SELECT COUNT(*) c FROM x) SELECT (SELECT AVG(r) FROM (SELECT r FROM x LIMIT 2 - (SELECT c FROM n)%2 OFFSET ((SELECT c FROM n)-1)/2)) AS med, (SELECT c FROM n)`
6. `SELECT COUNT(*) AS frozen_rows, MIN(row_no), MAX(row_no), MIN(inv_dc_current), MAX(inv_dc_current), MIN(bms_current), MAX(bms_current), MIN(inv_torque_feedback), MAX(inv_torque_feedback), (SELECT label FROM session WHERE session_id=3) FROM sample WHERE session_id=3 AND row_no BETWEEN 11979 AND 12279 AND inv_dc_current=44.1`
7. `SELECT SUM(bms_current<=0), SUM(inv_torque_feedback<=0), COUNT(*) FROM sample WHERE session_id=3 AND row_no BETWEEN 11979 AND 12279`
8. `SELECT COUNT(*) AS neg_rows, MIN(row_no), MAX(row_no), MIN(stm_ms), MAX(stm_ms) FROM sample_flags WHERE session_id=3 AND bad_ms=0 AND stm_ms<0`
