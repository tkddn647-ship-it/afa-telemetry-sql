# 분석 에이전트 보고서: 시험1

AI가 도구를 33번 오가며 96초 동안 조사. 주장 6개 중 SQL 재실행으로 **6개 재현됨**.

## 요약

I checked the quality of session '시험1' (16,869 rows) against the analysis rules v6. Recomputing the metrics with SQL gave a missing rate of 10.185283782344799% (1913 missing samples) and 103 broken rows (0.610587468136819%). There were 2 MCU restarts (rows 5174 and 16014) and 2 stopped intervals. The median bms_current/inv_dc_current ratio in the load interval was 0.7967072297780959. Of the warning rules, the missing rate, broken-row ratio and MCU restart warnings apply. On top of the metrics, I found two anomalies the quality metrics did not catch. (1) In rows 8410–8723 (314 rows), inv_dc_current is frozen at 144.6 A. In the same interval bms_current varies over 35.6–122.6 and torque over 22.3–127.7, and bad_inv is 0 for all of these rows. (2) In rows 11158–11457 (300 rows), vehicle_speed_kmh is exactly 0 while inv_motor_speed is 1269–2294 rpm. Right before (row 11157) it was 51.002 km/h and right after (row 11458) it was 32.949 km/h. bad_speed is 0 for all of these rows.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 10.185283782344799
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.7967072297780959

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **Sample missing rate exceeds 8%** Excluding bad_ms rows and computing stm_ms intervals per rule 3 gives 1913 missing samples and a missing rate of 10.185283782344799%. This exceeds the warning threshold of 8%. | 10.185283782344799 | 10.185283782344799 | 재현됨 |  |
| 2 | **Broken row ratio 0.61%** 103 rows have at least one of bad_ms, bad_inv, bad_bms, bad_speed or bad_value set to 1, which is 0.610587468136819% of all rows. This exceeds the threshold of 0.05%. | 0.610587468136819 | 0.610587468136819 | 재현됨 |  |
| 3 | **2 MCU restarts** stm_ms goes backwards twice: between rows 5173→5174 (263172→54582 ms) and between rows 16013→16014 (223892→38924 ms). There are also 2 stopped intervals over 1000 ms (rows 8065→8066 and 8141→8142). | 2 | 2 | 재현됨 | 5174~16014 |
| 4 | **Median pack-to-inverter current ratio in the load interval** Taking load rows with inv_dc_current > 25 A and excluding rows with bad_inv or bad_bms set leaves 4242 rows. The median bms_current/inv_dc_current ratio over these rows is 0.7967072297780959, which matches the basis for the 1.25 correction factor (about 0.80). | 0.7967072297780959 | 0.7967072297780959 | 재현됨 |  |
| 5 | **Inverter DC current frozen (not caught by the metrics)** In rows 8410–8723 (314 consecutive rows), inv_dc_current is frozen at exactly 144.6 A. It was 148.0 just before (row 8409) and 79.8 just after (row 8724). In the same interval bms_current varies over 35.6–122.6 A, inv_motor_speed over 2962–4032 and inv_torque_feedback over 22.3–127.7, and bad_inv and bad_bms are 0 for all 314 rows. The bms/inv ratio within this interval ranges from 0.246 to 0.848, which means the frozen values contaminate the load-interval ratio and violation metrics. | 314 | 314 | 재현됨 | 8410~8723 |
| 6 | **Vehicle speed drops to 0 (not caught by the metrics)** In rows 11158–11457 (300 consecutive rows), vehicle_speed_kmh is exactly 0 while inv_motor_speed is 1269–2294 rpm. Right before (row 11157) the speed was 51.002 km/h and right after (row 11458) it was 32.949 km/h. In normal rows the speed/rpm ratio is constant at about 0.02223, so a speed of 0 does not match the motor rotation. bad_speed is 0 for all 300 rows. These are the only rows in the session with speed 0 and motor speed above 500. | 300 | 300 | 재현됨 | 11158~11457 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) d, row_no - LAG(row_no) OVER (ORDER BY row_no) - 1 nb FROM sample_flags WHERE session_id=1 AND bad_ms=0), m AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) miss FROM g) SELECT miss*100.0/(miss+(SELECT COUNT(*) FROM sample WHERE session_id=1)) pct, miss FROM m`
2. `SELECT COUNT(*)*100.0/(SELECT COUNT(*) FROM sample WHERE session_id=1) pct, COUNT(*) FROM sample_flags WHERE session_id=1 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
3. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) d FROM sample_flags WHERE session_id=1 AND bad_ms=0) SELECT SUM(d<0) restarts, MIN(CASE WHEN d<0 THEN row_no END), MAX(CASE WHEN d<0 THEN row_no END), SUM(d>1000) stops FROM g`
4. `WITH r AS (SELECT bms_current*1.0/inv_dc_current x FROM sample_flags WHERE session_id=1 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT x, ROW_NUMBER() OVER (ORDER BY x) rn, COUNT(*) OVER () c FROM r) SELECT AVG(x), MIN(c) FROM o WHERE rn IN ((c+1)/2,(c+2)/2)`
5. `WITH s AS (SELECT row_no, inv_dc_current v, CASE WHEN inv_dc_current = LAG(inv_dc_current) OVER (ORDER BY row_no) THEN 0 ELSE 1 END chg FROM sample WHERE session_id=1), g AS (SELECT row_no, v, SUM(chg) OVER (ORDER BY row_no) grp FROM s) SELECT COUNT(*) n, v, MIN(row_no) first_row, MAX(row_no) last_row FROM g WHERE v > 25 GROUP BY grp ORDER BY n DESC LIMIT 1`
6. `SELECT COUNT(*) n, MIN(row_no) first_row, MAX(row_no) last_row, MIN(inv_motor_speed), MAX(inv_motor_speed) FROM sample WHERE session_id=1 AND vehicle_speed_kmh = 0 AND inv_motor_speed > 500`
