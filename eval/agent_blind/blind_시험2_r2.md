# 분석 에이전트 보고서: 시험2

AI가 도구를 23번 오가며 99초 동안 조사. 주장 7개 중 SQL 재실행으로 **7개 재현됨**.

## 요약

세션 '시험2'(32576행)의 품질 지표를 모두 SQL로 다시 계산했고, session_quality 값과 같았다. 빠진 샘플 1949개(누락률 약 5.65%), 깨진 행 105개(0.322%), 멈춘 구간 0번, MCU 재시작 2번(row 12093, 18233), 부하 구간 bms/inv 전류비 중앙값 0.7986이다. 누락 1949개 가운데 1696개는 stm_ms 간격이 19 ms인 자리에서 나왔다. 이 자리는 대부분 19행마다 한 번씩 규칙적으로 나타나므로, 무작위로 빠진 것이 아니라 주기적으로 한 샘플씩 빠지는 것으로 보인다. 지표에 안 잡히는 이상도 하나 찾았다. row 30336~30658(323행) 동안 inv_dc_current가 36.1 A로 고정돼 있었다. 같은 구간에서 bms_current는 21.8~46.3 A 사이 27가지 값으로, 토크는 29.4~56.3으로 계속 변했다. 그런데 이 행들은 bad_inv=0, bad_bms=0이라 부하 구간 분석에 그대로 들어간다. 세션 안 다른 곳에서 inv_dc_current가 가장 길게 같은 값을 유지한 것은 50행이다. 전류_불일치 지표의 최장 길이도 14행에 그쳐서 이 구간을 잡지 못한다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 5.645
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.7985611510791366

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **빠진 샘플 수** 분석 규칙 3번으로 계산하면 시험2에서 빠진 샘플은 1949개다. 받은 샘플이 32576개이므로 누락률은 1949/(32576+1949)*100, 약 5.645%다. | 1949 | 1949.0 | 재현됨 |  |
| 2 | **누락의 대부분은 19 ms 간격에서 나옴** 빠진 샘플 1949개 중 1696개는 stm_ms 간격이 19 ms인 1696곳에서 하나씩 나왔다. 바로 앞 간격은 보통 11 ms다. 19 ms 간격끼리의 row_no 차이는 대부분 19행(1616번)이다. 그래서 무작위로 빠진 것이 아니라 약 19행마다 한 샘플씩 규칙적으로 빠지는 것으로 보인다. | 1696 | 1696.0 | 재현됨 |  |
| 3 | **MCU 재시작 2번** bad_ms 행을 빼고 보면 stm_ms가 앞 행보다 작아진 곳이 2번 있다. row 12093에서 -211472 ms, row 18233에서 -79004 ms만큼 줄었다. | 2 | 2 | 재현됨 | 12093~18233 |
| 4 | **깨진 행 105개** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행은 105개다. 전체 32576행의 약 0.322%다. | 105 | 105 | 재현됨 |  |
| 5 | **부하 구간 팩/인버터 전류비 중앙값** 부하 구간(inv_dc_current>25 A이고 bad_inv=0, bad_bms=0)인 7217행에서 보정 전 bms_current/inv_dc_current 비율의 중앙값은 0.7985611510791366이다. | 0.7985611510791366 | 0.7985611510791366 | 재현됨 |  |
| 6 | **인버터 DC 전류가 36.1 A로 고정된 구간 (지표에 안 잡힘)** row 30336부터 30658까지 323행 동안 inv_dc_current가 36.1 A로 바뀌지 않았다. 세션 안에서 같은 값이 두 번째로 길게 이어진 것은 50행이다. 같은 구간에서 bms_current는 21.8~46.3 A 사이 27가지 값으로, inv_torque_feedback은 29.4~56.3으로 계속 변했다. 그래서 인버터 전류 값이 갱신되지 않은 것(고착)으로 보인다. 이 323행은 bad_inv=0, bad_bms=0이라 부하 구간 분석에 그대로 들어가고, 이 구간의 bms/inv 비율은 0.60~1.28로 흔들린다. 전류_불일치 지표의 최장 길이는 14행이라 이 구간을 잡지 못한다. | 323 | 323 | 재현됨 | 30336~30658 |
| 7 | **고정 구간에서도 팩 전류는 계속 변함** row 30336~30658의 부하 구간 323행에서 bms_current는 27가지 값을 가졌다. 인버터 전류만 멈춰 있었다는 뜻이다. | 323 | 323 | 재현됨 | 30336~30658 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) AS pm, LAG(row_no) OVER (ORDER BY row_no) AS pr FROM sample_flags WHERE session_id=2 AND bad_ms=0), d AS (SELECT row_no, pr, stm_ms-pm AS d FROM g WHERE pm IS NOT NULL) SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-(row_no-pr-1),0) ELSE 0 END) AS miss FROM d`
2. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) pm, LAG(row_no) OVER (ORDER BY row_no) pr FROM sample_flags WHERE session_id=2 AND bad_ms=0), d AS (SELECT row_no, pr, stm_ms-pm d FROM g WHERE pm IS NOT NULL) SELECT SUM(MAX(ROUND(d/10.0)-1-(row_no-pr-1),0)) FROM d WHERE d=19`
3. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) pm FROM sample_flags WHERE session_id=2 AND bad_ms=0) SELECT COUNT(*) FROM g WHERE stm_ms-pm<0`
4. `SELECT COUNT(*) FROM sample_flags WHERE session_id=2 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
5. `WITH r AS (SELECT bms_current*1.0/inv_dc_current x FROM sample_flags WHERE session_id=2 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT x, ROW_NUMBER() OVER (ORDER BY x) rn, COUNT(*) OVER () c FROM r) SELECT AVG(x) FROM o WHERE rn IN ((c+1)/2,(c+2)/2)`
6. `WITH c AS (SELECT row_no, inv_dc_current i, CASE WHEN inv_dc_current = LAG(inv_dc_current) OVER (ORDER BY row_no) THEN 0 ELSE 1 END ch FROM sample WHERE session_id=2), g AS (SELECT row_no, i, SUM(ch) OVER (ORDER BY row_no) grp FROM c) SELECT COUNT(*) n, MIN(row_no), MAX(row_no), MIN(i) FROM g WHERE i<>0 GROUP BY grp ORDER BY n DESC LIMIT 1`
7. `SELECT COUNT(*) n_load, COUNT(DISTINCT bms_current), MAX(bms_current/inv_dc_current), MIN(bms_current/inv_dc_current) FROM sample_flags WHERE session_id=2 AND row_no BETWEEN 30336 AND 30658 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0`
