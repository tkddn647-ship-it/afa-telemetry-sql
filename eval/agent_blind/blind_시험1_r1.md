# 분석 에이전트 보고서: 시험1

AI가 도구를 31번 오가며 111초 동안 조사. 주장 7개 중 SQL 재실행으로 **7개 재현됨**.

## 요약

시험1(16869행)을 분석 규칙 v6에 따라 조사했다. 누락률은 10.185283782344799%로, 빠진 샘플은 1913개이고 경고 기준 8%를 넘는다. 깨진 행은 103개(0.611%)이며 그중 시각 깨짐(bad_ms)이 60개다. MCU 재시작은 2번으로 row 5174와 16014에서 일어났고, 기록이 멈춘 구간도 2번(row 8066, 8142) 있다. 부하 구간(4242행)의 bms_current/inv_dc_current 중앙값은 0.7967072297780959다. 품질 지표에 안 잡히는 이상도 하나 찾았다. row 11158부터 11457까지 300행 동안 vehicle_speed_kmh가 정확히 0.0으로 끊겼다. 같은 구간에서 inv_motor_speed는 1269 rpm 이상이었고, 끊기기 직전 속도는 51.002 km/h, 직후는 32.949 km/h였다. 이 300행 중 bad_speed로 표시된 행은 0개라서 깨진 행 지표에 들어가지 않는다. 또 두 번의 MCU 재시작 지점에서 stm_ms는 크게 뒤로 갔지만 ts_utc는 같은 값으로 이어졌다. 특히 row 16014에서는 차량이 약 24.7 km/h로 달리던 중이었다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 10.185283782344799
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.7967072297780959

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률 10.19%** bad_ms 행을 빼고 stm_ms 간격으로 계산하면 빠진 샘플은 1913개이고, 누락률은 1913/(16869+1913)*100 = 10.185283782344799%다. 경고 기준 8%를 넘는다. | 10.185283782344799 | 10.185283782344799 | 재현됨 |  |
| 2 | **깨진 행 103개 (0.611%)** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행은 103개다. 항목별로는 시각 깨짐 60, 인버터 전류 튐 14, 팩 전류 튐 14, 속도 튐 15, 값 튐 43이며, 행 손상(n_bad_cols≥3)은 0이다. | 103 | 103 | 재현됨 |  |
| 3 | **시각(stm_ms) 깨진 행 60개** sample_flags에서 bad_ms=1인 행은 60개다. | 60 | 60 | 재현됨 |  |
| 4 | **MCU 재시작 2번 (row 5174, 16014)** 앞 행과의 stm_ms 간격이 음수인 곳이 2곳이다. row 5173→5174에서 263172→54582 ms, row 16013→16014에서 223892→38924 ms로 뒤로 갔다. 두 곳 모두 ts_utc는 앞 행과 같은 값으로 이어졌고, row 16014에서는 vehicle_speed_kmh가 24.678이었다. | 2 | 2 | 재현됨 | 5174~16014 |
| 5 | **기록 멈춤 2번 (row 8066, 8142)** 간격이 1000 ms를 넘는 곳이 2곳이다. row 8065→8066은 43960 ms이고 ts_utc도 07:19:53대에서 07:20:49대로 넘어간다. row 8141→8142는 1259 ms다. | 2 | 2 | 재현됨 | 8066~8142 |
| 6 | **부하 구간 팩/인버터 전류비 중앙값 0.797** inv_dc_current>25 A이고 bad_inv=0, bad_bms=0인 4242행에서 bms_current/inv_dc_current(보정 전 원본)의 중앙값은 0.7967072297780959다. scale_correction의 계수 1.25 근거(약 0.80)와 맞는다. | 0.7967072297780959 | 0.7967072297780959 | 재현됨 |  |
| 7 | **[지표 밖] 주행 중 차량 속도 신호 300행 0 고정 (row 11158~11457)** row 11158부터 11457까지 300행 연속으로 vehicle_speed_kmh가 정확히 0.0이다. 같은 구간의 inv_motor_speed는 최소 1269 rpm이고, 직전 row 11157의 속도는 51.002 km/h, 직후 row 11458은 32.949 km/h다. 세션 전체에서 '속도 0이면서 모터 500 rpm 초과'인 행은 이 300행뿐이다. 이 구간의 bad_speed 표시는 0개라서 품질 지표(속도_튐, 깨진_행)에 잡히지 않는다. | 300 | 300 | 재현됨 | 11158~11457 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) pm, LAG(row_no) OVER (ORDER BY row_no) pr FROM sample_flags WHERE session_id=1 AND bad_ms=0), d AS (SELECT row_no, pr, stm_ms-pm AS d FROM g WHERE pm IS NOT NULL), m AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-(row_no-pr-1),0) ELSE 0 END) miss FROM d) SELECT miss*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=1)+miss) AS pct FROM m`
2. `SELECT COUNT(*) FROM sample_flags WHERE session_id=1 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
3. `SELECT SUM(bad_ms) FROM sample_flags WHERE session_id=1`
4. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) pm FROM sample_flags WHERE session_id=1 AND bad_ms=0) SELECT SUM(stm_ms-pm<0) FROM g WHERE pm IS NOT NULL`
5. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) pm FROM sample_flags WHERE session_id=1 AND bad_ms=0) SELECT SUM(stm_ms-pm>1000) FROM g WHERE pm IS NOT NULL`
6. `WITH r AS (SELECT bms_current*1.0/inv_dc_current AS x FROM sample_flags WHERE session_id=1 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT x, ROW_NUMBER() OVER (ORDER BY x) rn, COUNT(*) OVER () n FROM r) SELECT AVG(x) FROM o WHERE rn IN ((n+1)/2,(n+2)/2)`
7. `SELECT COUNT(*) FROM sample WHERE session_id=1 AND vehicle_speed_kmh=0 AND inv_motor_speed>500`
