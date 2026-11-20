# 분석 에이전트 보고서: 시험1

AI가 도구를 20번 오가며 86초 동안 조사. 주장 6개 중 SQL 재실행으로 **6개 재현됨**.

## 요약

세션 '시험1'(16,869행)의 품질 지표를 분석 규칙 v6에 따라 SQL로 다시 계산했고, 모두 session_quality 값과 같았다. 누락률은 10.185283782344799%(빠진 샘플 1913개)로 경고 기준 8%를 넘는다. 깨진 행은 103개(0.611%)이고 그중 시각 깨짐(bad_ms)이 60행이다. MCU 재시작은 2번(row 5174, row 16014에서 stm_ms가 거꾸로 감)이고 기록이 멈춘 구간도 2번(row 8066, row 8142)이다. 부하 구간에서 bms_current/inv_dc_current 비율의 중앙값은 0.7967072297780959로, 보정 계수 1.25가 필요하다는 판단과 맞는다. 지표에 잡히지 않은 이상도 2개 찾았다. (1) row 8410~8723(314행)에서 inv_dc_current가 144.6 A에 멈춰 있다. 같은 구간에서 bms_current(35.6~122.6 A), 회전수, 토크, 차속은 계속 변한다. (2) row 11158~11457(300행)에서 vehicle_speed_kmh가 정확히 0인데, 모터 회전수는 1269~2294 rpm이다. 바로 앞 행에서는 51.002 km/h였고 바로 뒤 행에서는 32.949 km/h로 돌아온다. 두 구간 모두 sample_flags의 bad_inv, bad_bms, bad_speed, bad_value 표시가 하나도 없다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 10.185283782344799
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.7967072297780959

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률 8% 초과** bad_ms 행을 빼고 row_no 순서로 stm_ms 간격을 계산했다. 15<d<=1000 구간에서 빠진 샘플은 1913개이고, 누락률은 1913/(16869+1913)*100 = 10.185283782344799%로 경고 기준 8%를 넘는다. | 10.185283782344799 | 10.185283782344799 | 재현됨 | 1~16869 |
| 2 | **주행 중 MCU 재시작 2번** bad_ms 행을 뺀 상태에서 stm_ms가 앞 행보다 작아진 곳이 2번 있다. row 5174(263172→54582)와 row 16014(223892→38924)다. 이와 별도로 간격이 1000 ms를 넘어 기록이 멈춘 구간도 2번(row 8066, row 8142) 있다. | 2 | 2 | 재현됨 | 5174~16014 |
| 3 | **깨진 행 103개 (0.611%)** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행은 103개로, 전체 16869행의 약 0.611%다. 경고 기준 0.05%를 넘는다. 그중 시각 깨짐(bad_ms) 행은 60개다. | 103 | 103 | 재현됨 |  |
| 4 | **부하 구간 팩/인버터 전류비 중앙값 0.797** 부하 구간은 inv_dc_current>25 A이고 bad_inv=0, bad_bms=0인 행으로 4242행이다. 이 구간에서 bms_current/inv_dc_current의 중앙값은 0.7967072297780959로, scale_correction의 계수 1.25(=1/0.8)와 맞는다. | 0.7967072297780959 | 0.7967072297780959 | 재현됨 |  |
| 5 | **인버터 DC 전류가 144.6 A에 멈춤 (지표에 안 잡힘)** row 8410~8723(314행, stm_ms 135292~139582) 동안 inv_dc_current 값은 144.6 하나뿐이다. 같은 구간에서 bms_current는 35.6~122.6 A 사이에서 41가지 값으로 변하고, 모터 회전수는 2962~4032 rpm, 토크 피드백은 22.3~127.7, 차속은 65.9~89.6 km/h로 변한다. 이 구간의 bms/inv 전류비 중앙값은 0.6507607192254495로 정상값 약 0.80과 다르다. 그러므로 인버터 전류 값이 갱신되지 않고 멈춘 것이다. 이 구간에는 bad_inv, bad_bms, bad_value 표시가 하나도 없어 부하 구간 분석에 그대로 들어간다. | 314 | 314 | 재현됨 | 8410~8723 |
| 6 | **모터는 돌고 있는데 차속이 0 (신호 모순, 지표에 안 잡힘)** row 11158~11457(300행) 동안 vehicle_speed_kmh는 정확히 0이다. 그런데 같은 구간의 inv_motor_speed는 1269~2294 rpm이고 inv_dc_current는 최대 64.6 A다. 차속은 바로 앞 row 11157에서 51.002 km/h였다가 갑자기 0이 되고, 바로 뒤 row 11458에서 32.949 km/h로 돌아온다. 세션 전체에서 모터 회전수가 500 rpm을 넘으면서 차속이 0인 행은 이 300행뿐이다. 이 구간에 bad_speed 표시는 없다. | 300 | 300 | 재현됨 | 11158~11457 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) AS pm, LAG(row_no) OVER (ORDER BY row_no) AS pr FROM sample_flags WHERE session_id=1 AND bad_ms=0), d AS (SELECT row_no, stm_ms-pm AS d, row_no-pr-1 AS nb FROM g WHERE pm IS NOT NULL) SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END)*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=1)+SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END)) AS miss_pct, SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) AS missing FROM d`
2. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) AS d FROM sample_flags WHERE session_id=1 AND bad_ms=0) SELECT SUM(d<0) AS restarts, SUM(d>1000) AS stalls FROM g`
3. `SELECT (SELECT COUNT(*) FROM sample_flags WHERE session_id=1 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)) AS broken, (SELECT COUNT(*) FROM sample_flags WHERE session_id=1 AND bad_ms=1) AS bad_ms_rows`
4. `WITH l AS (SELECT bms_current*1.0/inv_dc_current r FROM sample_flags WHERE session_id=1 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT r, ROW_NUMBER() OVER (ORDER BY r) rn, COUNT(*) OVER () n FROM l) SELECT AVG(r) median, MAX(n) n FROM o WHERE rn IN ((n+1)/2,(n+2)/2)`
5. `SELECT COUNT(*), COUNT(DISTINCT inv_dc_current), COUNT(DISTINCT bms_current) FROM sample WHERE session_id=1 AND row_no BETWEEN 8410 AND 8723`
6. `SELECT COUNT(*) n, MIN(row_no), MAX(row_no) FROM sample WHERE session_id=1 AND inv_motor_speed>500 AND vehicle_speed_kmh=0`
