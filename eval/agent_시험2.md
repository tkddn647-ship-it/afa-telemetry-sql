# 분석 에이전트 보고서: 시험2

AI가 도구를 25번 오가며 96초 동안 조사. 주장 8개 중 SQL 재실행으로 **8개 재현됨**.

## 요약

세션 '시험2'(32587행)를 분석 규칙 v4로 다시 계산했다. 빠진 샘플은 1938개로 session_quality와 같다(옛 정의로 세면 1998개). 누락률은 반올림하지 않으면 5.613323678493845%이고, 기록이 멈춘 구간은 0번이다. MCU 재시작은 2번으로 row 12134와 row 18295에서 stm_ms가 거꾸로 간다. 깨진 행은 89행(0.273%)이고, 부하 구간에서 팩/인버터 전류 비율 중앙값은 0.7934186471663619이다. 지표에 잡히지 않은 이상은 세 가지다. (1) row 24144~24449의 306행에서 inv_dc_current가 58.9 A에 멈춰 있다. 같은 구간에서 모터 속도는 1250~1920 rpm, bms_current는 -1.9~45.7 A로 계속 바뀐다. (2) 그 구간 가운데 208행(row 24203~24410)은 인버터 전류가 58.9 A로 부하 구간인데 팩 전류는 5 A 미만이어서 두 신호가 서로 모순된다. 이 구간을 빼면 비율 중앙값은 0.7957166392092256이 된다. (3) bad 플래그에 안 걸린 단일 행 튐도 있다. row 5231과 row 7594는 인버터 전압이 0 V이고 모터 속도가 0인데 inv_dc_current가 133.6 A와 83.9 A로 나와 부하 구간에 들어간다. row 24926은 bms_voltage가 78.1 V인데 앞뒤 행은 278.1 V다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 5.613323678493845
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.7934186471663619

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **누락률 (규칙 v4, 반올림 안 함)** bad_ms 행을 빼고 간격을 계산하고, 두 행 사이 bad_ms 행 수를 빼면 빠진 샘플은 1938개다. 누락률은 1938/(32587+1938)*100 = 5.613323678493845%다. session_quality는 이 값을 5.6으로 반올림해 보여 준다. | 5.613323678493845 | 5.613323678493845 | 재현됨 |  |
| 2 | **MCU 재시작 2번** bad_ms가 아닌 행끼리 비교하면 stm_ms가 두 번 거꾸로 간다. row 12134에서는 264782에서 52900으로, row 18295에서는 118450에서 39266으로 바뀐다. 기록이 멈춘 구간(d>1000)은 0번이다. | 2 | 2 | 재현됨 | 12134~18295 |
| 3 | **부하 구간 팩/인버터 전류 비율 중앙값** 부하 구간(inv_dc_current>25, bad_inv=0, bad_bms=0) 7451행에서 bms_current(원본)/inv_dc_current의 중앙값은 0.7934186471663619다. | 0.7934186471663619 | 0.7934186471663619 | 재현됨 |  |
| 4 | **인버터 DC 전류가 58.9 A에 멈춘 구간** row 24144부터 24449까지 306행 동안 inv_dc_current가 58.9 A 한 값만 가진다. 같은 구간에서 inv_motor_speed는 1250~1920 rpm, bms_current는 -1.9~45.7 A(서로 다른 값 21개), 차속은 27.8~42.7 km/h로 계속 바뀐다. 이 구간의 bad_inv 합은 0이라 품질 지표에는 잡히지 않는다. 바로 앞 row 24143은 24.1 A, 바로 뒤 row 24450은 17.0 A다. | 306 | 306 | 재현됨 | 24144~24449 |
| 5 | **부하 구간인데 팩 전류는 거의 0인 모순** 멈춘 구간 가운데 row 24203~24410의 208행은 inv_dc_current가 58.9 A로 부하 구간에 들어가지만, bms_current는 -1.9~2.5 A(5 A 미만)여서 두 전류 신호가 서로 모순된다. 이 이상한 행들은 비율 중앙값 계산에 그대로 들어간다. 24144~24449 구간을 빼고 다시 계산하면 중앙값은 0.7934186471663619에서 0.7957166392092256으로 바뀐다(대상 7145행). | 208 | 208 | 재현됨 | 24203~24410 |
| 6 | **멈춘 구간을 뺀 비율 중앙값** row 24144~24449를 빼면 부하 구간 비율 중앙값은 0.7957166392092256이다(7145행). | 0.7957166392092256 | 0.7957166392092256 | 재현됨 | 24144~24449 |
| 7 | **전압 0 V인데 인버터 전류가 큰 행 (튐 플래그 안 걸림)** row 5231(133.6 A)과 row 7594(83.9 A)는 inv_voltage가 0 V, inv_motor_speed가 0, bms_current가 0인데 inv_dc_current만 크다. 두 행 모두 bad_inv=0이라 부하 구간 계산에 들어간다. | 2 | 2 | 재현됨 | 5231~7594 |
| 8 | **팩 전압 단일 행 튐 (플래그 없음)** row 24926의 bms_voltage는 78.1 V다. 바로 앞뒤 행(24925, 24927)은 278.1 V이고, 같은 행의 inv_voltage는 280.6 V다. 이 행은 bad_bms=0이고 sample_flags에 팩 전압용 bad 플래그는 없다. | 78.1 | 78.1 | 재현됨 | 24926~24926 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) AS pms, LAG(row_no) OVER (ORDER BY row_no) AS prn FROM sample_flags WHERE session_id=2 AND bad_ms=0), d AS (SELECT stm_ms-pms AS d, row_no-prn-1 AS nb FROM g WHERE pms IS NOT NULL), m AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) AS miss FROM d) SELECT miss*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=2)+miss) AS pct FROM m`
2. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) AS pms FROM sample_flags WHERE session_id=2 AND bad_ms=0) SELECT COUNT(*) FROM g WHERE stm_ms-pms<0`
3. `WITH r AS (SELECT bms_current*1.0/inv_dc_current AS x FROM sample_flags WHERE session_id=2 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT x, ROW_NUMBER() OVER (ORDER BY x) rn, COUNT(*) OVER () n FROM r) SELECT AVG(x) FROM o WHERE rn IN ((n+1)/2,(n+2)/2)`
4. `SELECT COUNT(*) FROM sample_flags WHERE session_id=2 AND row_no BETWEEN 24144 AND 24449 AND inv_dc_current=58.9 AND bad_inv=0`
5. `SELECT COUNT(*) FROM sample_flags WHERE session_id=2 AND row_no BETWEEN 24203 AND 24410 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0 AND bms_current<5`
6. `WITH r AS (SELECT bms_current*1.0/inv_dc_current AS x FROM sample_flags WHERE session_id=2 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0 AND row_no NOT BETWEEN 24144 AND 24449), o AS (SELECT x, ROW_NUMBER() OVER (ORDER BY x) rn, COUNT(*) OVER () n FROM r) SELECT AVG(x) FROM o WHERE rn IN ((n+1)/2,(n+2)/2)`
7. `SELECT COUNT(*) FROM sample_flags WHERE session_id=2 AND inv_dc_current>25 AND inv_voltage=0 AND bad_inv=0`
8. `SELECT bms_voltage FROM sample_flags WHERE session_id=2 AND row_no=24926 AND bad_bms=0`
