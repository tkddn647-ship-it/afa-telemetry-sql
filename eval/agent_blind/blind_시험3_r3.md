# 분석 에이전트 보고서: 시험3

AI가 도구를 37번 오가며 128초 동안 조사. 주장 8개 중 SQL 재실행으로 **8개 재현됨**.

## 요약

시험3(24,061행)의 품질 지표를 SQL로 다시 계산해 확인했다. 누락률 10.617036294067388%(빠진 샘플 2858개), 깨진 행 107개, MCU 재시작 4번, 부하 구간 팩/인버터 전류비 중앙값 0.79585326953748로 모두 session_quality 값과 맞는다. session_quality는 누락률 10.6을 반올림해 보여 주므로, 규칙 7에 따라 반올림하지 않은 값을 썼다. 지표에 안 잡히는 이상은 네 가지를 찾았다. (1) MCU 재시작 4번 중 19248행과 23397행에서는 ts_utc가 각각 약 85초와 664초 건너뛴다. 멈춘_구간 지표는 1번이지만 실제 기록 공백은 이 2번이 더 있다. (2) 4번 중 17710행 재시작만 주접촉기가 닫혀 있고 모터가 406 rpm으로 도는 주행 중에 일어났다. (3) 19248행부터 세션 끝인 24061행까지 4814행 동안 인버터 전압·IGBT 온도·모터 온도·모터 속도·주접촉기가 모두 정확히 0이다. 같은 구간에서 BMS 전압은 271.3~272.9 V로 살아 있다. (4) bms_charge는 세션 전체 24061행에서 0이고, bms_ccl은 12, bms_dcl은 190으로 바뀌지 않는다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 10.617036294067388
- broken_timestamp_rows: 60
- mcu_restarts: 4
- pack_to_inverter_ratio_median: 0.79585326953748

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률** bad_ms 행을 뺀 stm_ms 간격으로 빠진 샘플을 세면 2858개이고, 누락률은 10.617036294067388%로 경고 기준 8%를 넘는다. | 10.617036294067388 | 10.617036294067388 | 재현됨 |  |
| 2 | **깨진 행 수** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행은 107개다. | 107 | 107 | 재현됨 |  |
| 3 | **MCU 재시작 횟수** stm_ms 간격이 음수인 곳은 4번(17710, 19248, 19712, 23397행)이다. 간격 1000 ms 초과로 멈춘 곳은 557행 1번이다. | 4 | 4 | 재현됨 | 17710~23397 |
| 4 | **재시작과 겹친 기록 공백 (지표에 없음)** 19248행과 23397행에서는 stm_ms가 뒤로 가는 동시에 ts_utc가 각각 85.1초와 663.9초 건너뛴다. 멈춘_구간 지표는 1번이지만, 재시작으로만 세진 기록 공백이 2번 더 있다. | 2 | 2 | 재현됨 | 19248~23397 |
| 5 | **주행 중 MCU 재시작 (지표에 없음)** 재시작 4번 중 주접촉기가 닫힌(motor_main_contactor=1) 상태에서 일어난 것은 17710행 1번이다. 이때 모터 속도는 406 rpm이었다. stm_ms는 1184152에서 59558로 되돌아갔지만 ts_utc는 이어진다. | 1 | 1 | 재현됨 | 17710~17710 |
| 6 | **인버터 신호 전체 0 구간 (지표에 없음)** 19248행부터 세션 끝인 24061행까지 4814행(세션의 약 20%) 동안 인버터 전압, IGBT 온도, 모터 온도, 모터 속도, 주접촉기가 모두 정확히 0이다. 바로 앞 19247행의 IGBT 온도는 37.2, 모터 온도는 45.6이었다. 같은 구간의 BMS 전압은 271.3~272.9 V로 계속 기록된다. | 4814 | 4814 | 재현됨 | 19248~24061 |
| 7 | **BMS 충전 상태 신호 고정 (지표에 없음)** bms_charge는 세션 전체 24061행에서 0이다. bms_ccl은 12, bms_dcl은 190으로 세션 내내 한 값만 나온다. | 24061 | 24061 | 재현됨 | 1~24061 |
| 8 | **부하 구간 팩/인버터 전류비 중앙값** 부하 구간(inv_dc_current > 25 A, bad_inv·bad_bms 행 제외) 5964행에서 bms_current/inv_dc_current 중앙값은 0.79585326953748이다. | 0.79585326953748 | 0.79585326953748 | 재현됨 |  |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) AS pm, LAG(row_no) OVER (ORDER BY row_no) AS pr FROM sample_flags WHERE session_id=3 AND bad_ms=0), d AS (SELECT stm_ms-pm AS d, row_no-pr-1 AS nb FROM g WHERE pm IS NOT NULL), m AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) AS miss FROM d) SELECT miss*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=3)+miss) AS missing_pct, miss FROM m`
2. `SELECT COUNT(*) FROM sample_flags WHERE session_id=3 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
3. `WITH g AS (SELECT row_no, stm_ms-LAG(stm_ms) OVER (ORDER BY row_no) AS d FROM sample_flags WHERE session_id=3 AND bad_ms=0) SELECT SUM(d<0), SUM(d>1000) FROM g`
4. `WITH t AS (SELECT row_no, julianday(substr(ts_utc,1,4)||'-'||substr(ts_utc,6,2)||'-'||substr(ts_utc,9,2)||substr(ts_utc,11))*86400 AS s FROM sample WHERE session_id=3), u AS (SELECT row_no, s - LAG(s) OVER (ORDER BY row_no) dt FROM t) SELECT COUNT(*), MIN(row_no), MAX(row_no), MIN(dt), MAX(dt) FROM u WHERE dt>60`
5. `WITH g AS (SELECT row_no, stm_ms, motor_main_contactor c, inv_motor_speed m, LAG(stm_ms) OVER (ORDER BY row_no) AS pm FROM sample_flags WHERE session_id=3 AND bad_ms=0) SELECT COUNT(*), MIN(row_no), MAX(row_no), MIN(m) FROM g WHERE stm_ms-pm<0 AND c=1`
6. `SELECT COUNT(*), MIN(row_no), MAX(row_no), MIN(bms_voltage), MAX(bms_voltage) FROM sample WHERE session_id=3 AND row_no>=19248 AND inv_voltage=0 AND inv_temp_igt=0 AND inv_temp_motor=0 AND inv_motor_speed=0 AND motor_main_contactor=0`
7. `SELECT SUM(bms_charge=0), COUNT(*), MIN(bms_ccl), MAX(bms_ccl), MIN(bms_dcl), MAX(bms_dcl) FROM sample WHERE session_id=3`
8. `WITH a AS (SELECT s.bms_current*1.0/s.inv_dc_current r FROM sample s JOIN sample_flags f USING(session_id,row_no) WHERE s.session_id=3 AND s.inv_dc_current>25 AND f.bad_inv=0 AND f.bad_bms=0), o AS (SELECT r, ROW_NUMBER() OVER (ORDER BY r) rn, COUNT(*) OVER () n FROM a) SELECT AVG(r), MAX(n) FROM o WHERE rn IN ((n+1)/2, (n+2)/2)`
