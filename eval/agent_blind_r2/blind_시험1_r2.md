# 분석 에이전트 보고서: 시험1

AI가 도구를 29번 오가며 107초 동안 조사. 주장 9개 중 SQL 재실행으로 **9개 재현됨**.

## 요약

세션 '시험1'(16854행)을 분석 규칙 v6대로 SQL로 다시 계산했고, session_quality 값과 모두 맞았다. 누락률은 10.265147481631349%로 경고 기준 8%를 넘는다(빠진 샘플 1928개, 멈춘 구간 2번). 깨진 행은 105개이고 그중 시각(stm_ms)이 깨진 행이 60개다. MCU 재시작은 2번으로 row 6071과 16067에서 stm_ms가 거꾸로 간다. 부하 구간의 팩/인버터 전류비 중앙값은 0.7921146953405018이다(4286행). 지표에 안 잡히는 이상도 직접 찾았다. 첫째, row 8279~8588(310행) 동안 inv_dc_current가 146.7 A에서 바뀌지 않는다. 같은 구간에서 bms_current는 35.6~122.6 A, 토크 피드백은 서로 다른 값 36개, 모터 속도는 서로 다른 값 37개로 계속 변하는데도 그렇고, bad_inv 표시는 0이다. 이 310행은 모두 부하 구간이라 전류비 계산에 들어간다. 이 구간을 빼면 중앙값은 0.7935962523344907이다. 둘째, bms_charge가 세션 전체 16854행에서 0이다. 셋째, can2가 0인 단독 행이 5개 있다(row 5946~15143 사이에 흩어져 있음).

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 10.265147481631349
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.7921146953405018

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률 8% 초과** 규칙 3대로 계산하면 빠진 샘플은 1928개, 누락률은 10.265147481631349%이다. 경고 기준 8%를 넘는다. | 10.265147481631349 | 10.265147481631349 | 재현됨 |  |
| 2 | **시각(stm_ms) 깨진 행** sample_flags에서 bad_ms=1인 행이 60개 있다. | 60 | 60 | 재현됨 |  |
| 3 | **깨진 행 전체** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행이 105개다(전체의 0.623%). | 105 | 105 | 재현됨 |  |
| 4 | **MCU 재시작 2번** bad_ms 행을 빼고 보면 앞 행보다 stm_ms가 작아지는 곳이 2군데 있다. row 6070→6071(-242113 ms)과 row 16066→16067(-144856 ms)이다. | 2 | 2 | 재현됨 | 6071~16067 |
| 5 | **부하 구간 팩/인버터 전류비 중앙값** 부하 구간(inv_dc_current>25, bad_inv·bad_bms 행 제외, 4286행)에서 bms_current/inv_dc_current 중앙값은 0.7921146953405018이다. | 0.7921146953405018 | 0.7921146953405018 | 재현됨 |  |
| 6 | **[지표 밖] 인버터 DC 전류 146.7 A 고착** row 8279~8588(310행, 속도 60 km/h 이상) 동안 inv_dc_current가 146.7 A에서 바뀌지 않는다. 같은 구간에서 bms_current(35.6~122.6 A), 토크 피드백(서로 다른 값 36개), 모터 속도(서로 다른 값 37개)는 계속 변한다. bad_inv 표시는 0이라 품질 지표에 잡히지 않는다. 주행 중 같은 값이 가장 오래 이어진 구간이다. | 310 | 310 | 재현됨 | 8279~8588 |
| 7 | **[지표 밖] 고착 구간을 뺀 전류비 중앙값** 고착 구간 row 8279~8588을 부하 구간에서 빼면 행은 3976개, 전류비 중앙값은 0.7935962523344907이다. 고착 구간은 전류비 계산에 섞여 들어가 있다. | 0.7935962523344907 | 0.7935962523344907 | 재현됨 | 8279~8588 |
| 8 | **[지표 밖] 배터리 충전량(bms_charge) 전 구간 0** 세션 전체 16854행에서 bms_charge가 0이다(최소·최대 모두 0). 이 신호는 세션 내내 기록되지 않았다. | 16854 | 16854 | 재현됨 | 1~16854 |
| 9 | **[지표 밖] can2 상태 0인 단독 행** can2가 0인 행이 5개 있다. row 5946, 8468, 8505, 10451, 15143으로, 모두 한 행씩 떨어져 있다. | 5 | 5 | 재현됨 | 5946~15143 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) AS pm, LAG(row_no) OVER (ORDER BY row_no) AS pr FROM sample_flags WHERE session_id=1 AND bad_ms=0), d AS (SELECT row_no, pr, stm_ms-pm AS d FROM g WHERE pm IS NOT NULL), m AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-(row_no-pr-1),0) ELSE 0 END) AS miss FROM d) SELECT miss*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=1)+miss) FROM m`
2. `SELECT COUNT(*) FROM sample_flags WHERE session_id=1 AND bad_ms=1`
3. `SELECT COUNT(*) FROM sample_flags WHERE session_id=1 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
4. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) AS d FROM sample_flags WHERE session_id=1 AND bad_ms=0) SELECT COUNT(*) FROM g WHERE d < 0`
5. `WITH r AS (SELECT bms_current*1.0/inv_dc_current AS q FROM sample_flags WHERE session_id=1 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT q, ROW_NUMBER() OVER (ORDER BY q) rn, COUNT(*) OVER () n FROM r) SELECT AVG(q), MAX(n) FROM o WHERE rn IN ((n+1)/2, (n+2)/2)`
6. `WITH s AS (SELECT row_no, inv_dc_current v, vehicle_speed_kmh sp, CASE WHEN inv_dc_current = LAG(inv_dc_current) OVER (ORDER BY row_no) THEN 0 ELSE 1 END chg FROM sample WHERE session_id=1), g AS (SELECT *, SUM(chg) OVER (ORDER BY row_no) grp FROM s) SELECT COUNT(*) AS n, MIN(row_no) AS first_row, MAX(row_no) AS last_row, MIN(v) AS value_a FROM g GROUP BY grp HAVING MIN(sp) > 5 ORDER BY n DESC LIMIT 1`
7. `WITH r AS (SELECT bms_current*1.0/inv_dc_current AS q FROM sample_flags WHERE session_id=1 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0 AND row_no NOT BETWEEN 8279 AND 8588), o AS (SELECT q, ROW_NUMBER() OVER (ORDER BY q) rn, COUNT(*) OVER () n FROM r) SELECT AVG(q), MAX(n) FROM o WHERE rn IN ((n+1)/2, (n+2)/2)`
8. `SELECT COUNT(*) FROM sample WHERE session_id=1 AND bms_charge=0`
9. `SELECT COUNT(*) FROM sample WHERE session_id=1 AND can2=0`
