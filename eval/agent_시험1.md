# 분석 에이전트 보고서: 시험1

AI가 도구를 45번 오가며 162초 동안 조사. 주장 10개 중 SQL 재실행으로 **10개 재현됨**.

## 요약

세션 '시험1'(16,945행)을 분석 규칙 v4로 다시 계산했다. 빠진 샘플은 1,836개이고 누락률은 9.775837282359833%로 8% 경고 기준을 넘는다. session_quality 의 9.8은 이 값을 반올림한 것이다. 옛 v3 정의(깨진 시각 행도 빠진 샘플로 셈)로 세면 1,896개가 되는데, 이 도구는 v4 기준인 1,836개를 쓰고 있었다. 깨진 행은 85개(0.5016228976099144%)이고, 그중 시각이 깨진 행(bad_ms)이 60개다. MCU 재시작은 2번(row 5237, 16116), 기록이 멈춘 구간은 2번(row 8078, 8155)이다. 부하 구간(inv_dc_current > 25 A, bad_inv·bad_bms 제외, 4,427행)에서 bms_current/inv_dc_current 비율의 중앙값은 0.8007299270072993으로, 1.25 보정 계수의 근거와 맞는다. 품질 지표에 안 잡히는 이상은 세 가지를 찾았다. (1) row 9826~10129(304행) 동안 inv_dc_current 가 52.0 A에 멈춰 있었다. 같은 구간에서 bms_current 는 -2.1~71.4 A, 토크 피드백은 -3.5~114.6으로 계속 바뀌었고, bms_current 가 0 이하인 행도 86개 있어 두 전류 신호가 서로 맞지 않는다. 다른 구간에서 25 A를 넘는 같은 값이 이어진 최장 길이는 29행이었다. 이 304행은 플래그가 없어 부하 구간과 비율 계산에 그대로 들어간다. (2) row 1~4941(4,941행) 동안 bms_voltage 가 정확히 284.9 V로 고정됐다. 같은 구간에서 inv_voltage 는 0~89.6 V 사이에서 바뀌었다. (3) row 1496, 1693, 2783, 5877, 16649 의 5개 행은 inv_dc_current 가 앞뒤 행(5 A 미만)과 달리 혼자 25 A를 넘게 튀었고 bms_current 는 10 A 미만이었다. 이 행들은 bad_inv 플래그가 0이어서 부하 행으로 세어진다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 9.775837282359833
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.8007299270072993

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률 (규칙 v4)** 10 ms 주기 기준으로 빠진 샘플은 1,836개다. 누락률은 9.775837282359833%로 8% 경고 기준을 넘는다. session_quality 의 9.8은 이 값을 반올림한 것이다. | 9.775837282359833 | 9.775837282359833 | 재현됨 |  |
| 2 | **깨진 행 수** bad_ms, bad_inv, bad_bms, bad_speed 중 하나라도 1인 행은 85개로, 전체의 0.5016228976099144%다. 0.05% 경고 기준을 넘는다. | 85 | 85 | 재현됨 |  |
| 3 | **깨진 시각(stm_ms) 행** stm_ms 값이 깨진 행(bad_ms=1)은 60개다. | 60 | 60 | 재현됨 |  |
| 4 | **MCU 재시작** bad_ms 행을 빼고 앞 행과의 stm_ms 간격이 음수가 된 곳이 2번 있다. 위치는 row 5237과 row 16116이다. | 2 | 2 | 재현됨 | 5237~16116 |
| 5 | **기록 멈춤 구간** 간격이 1000 ms를 넘는 기록 멈춤이 2번 있다. row 8078 직전 간격은 43,960 ms, row 8155 직전 간격은 1,259 ms다. | 2 | 2 | 재현됨 | 8078~8155 |
| 6 | **팩/인버터 전류 비율 중앙값** 부하 구간 4,427행에서 bms_current/inv_dc_current 비율의 중앙값은 0.8007299270072993이다. 1.25 보정 계수(1/0.8)의 근거와 맞는다. | 0.8007299270072993 | 0.8007299270072993 | 재현됨 |  |
| 7 | **인버터 DC 전류 값 멈춤 (지표에 없음)** row 9826~10129의 304행 연속으로 inv_dc_current 가 52.0 A에 고정돼 있다. 25 A를 넘는 같은 값이 이어진 구간 중 가장 길고, 두 번째로 긴 구간은 29행이다. 이 구간은 bad_inv, bad_bms 플래그가 모두 0이어서 품질 지표에 잡히지 않는다. | 304 | 304 | 재현됨 | 9826~10129 |
| 8 | **멈춘 인버터 전류와 팩 전류의 모순** row 9826~10129 구간에서 inv_dc_current 는 52.0 A 부하를 가리키지만, 304행 중 86행은 bms_current 가 0 이하다. 같은 구간에서 bms_current 는 -2.1~71.4 A, inv_torque_feedback 은 -3.5~114.6으로 계속 바뀌어 두 신호가 서로 맞지 않는다. | 86 | 86 | 재현됨 | 9826~10129 |
| 9 | **팩 전압 값 멈춤 (지표에 없음)** 세션 시작인 row 1부터 row 4941까지 4,941행 연속으로 bms_voltage 가 정확히 284.9 V다. 세션 안에서 가장 긴 고정 구간이다. 같은 구간에서 inv_voltage 는 0~89.6 V 사이에서 바뀌었다. | 4941 | 4941 | 재현됨 | 1~4941 |
| 10 | **플래그 없는 단발 인버터 전류 튐** inv_dc_current 가 앞뒤 행(5 A 미만)과 달리 혼자 25 A를 넘었고 bms_current 는 10 A 미만인 행이 5개 있다(row 1496, 1693, 2783, 5877, 16649). 모두 bad_inv=0 이라서 부하 행으로 세어진다. | 5 | 5 | 재현됨 | 1496~16649 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) pm, LAG(row_no) OVER (ORDER BY row_no) pr FROM sample_flags WHERE session_id=1 AND bad_ms=0), d AS (SELECT stm_ms-pm d, row_no-pr-1 nb FROM g WHERE pm IS NOT NULL), m AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) x FROM d) SELECT x*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=1)+x) AS missing_rate_pct FROM m`
2. `SELECT SUM(MAX(bad_ms,bad_inv,bad_bms,bad_speed)) broken, SUM(bad_ms) FROM sample_flags WHERE session_id=1`
3. `SELECT SUM(bad_ms) bad_ms FROM sample_flags WHERE session_id=1`
4. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) d FROM sample_flags WHERE session_id=1 AND bad_ms=0) SELECT SUM(d<0) restarts, SUM(d>1000) stops, MIN(CASE WHEN d<0 THEN row_no END), MAX(CASE WHEN d<0 THEN row_no END) FROM g`
5. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) d FROM sample_flags WHERE session_id=1 AND bad_ms=0) SELECT SUM(d>1000) stops, MIN(CASE WHEN d>1000 THEN row_no END), MAX(CASE WHEN d>1000 THEN row_no END) FROM g`
6. `WITH r AS (SELECT bms_current*1.0/inv_dc_current x FROM sample_flags WHERE session_id=1 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT x, ROW_NUMBER() OVER (ORDER BY x) rn, COUNT(*) OVER () c FROM r) SELECT AVG(x) median_ratio, MAX(c) n FROM o WHERE rn IN ((c+1)/2, (c+2)/2)`
7. `WITH s AS (SELECT row_no, inv_dc_current v, CASE WHEN inv_dc_current=LAG(inv_dc_current) OVER (ORDER BY row_no) THEN 0 ELSE 1 END ch FROM sample WHERE session_id=1), g AS (SELECT *, SUM(ch) OVER (ORDER BY row_no) grp FROM s) SELECT COUNT(*) n, MIN(row_no) a, MAX(row_no) b, v FROM g GROUP BY grp HAVING v>25 ORDER BY n DESC LIMIT 1`
8. `SELECT SUM(bms_current<=0) bms_nonpos, COUNT(*) n FROM sample_flags WHERE session_id=1 AND row_no BETWEEN 9826 AND 10129`
9. `WITH s AS (SELECT row_no, bms_voltage v, CASE WHEN bms_voltage=LAG(bms_voltage) OVER (ORDER BY row_no) THEN 0 ELSE 1 END ch FROM sample WHERE session_id=1), g AS (SELECT *, SUM(ch) OVER (ORDER BY row_no) grp FROM s) SELECT COUNT(*) n, MIN(row_no) a, MAX(row_no) b, v FROM g GROUP BY grp ORDER BY n DESC LIMIT 1`
10. `SELECT COUNT(*) n, MIN(row_no), MAX(row_no) FROM sample_flags WHERE session_id=1 AND bad_inv=0 AND bad_bms=0 AND inv_dc_current>25 AND p_inv<5 AND n_inv<5 AND ABS(bms_current)<10`
