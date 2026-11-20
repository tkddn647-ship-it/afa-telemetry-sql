# 분석 에이전트 보고서: 시험3

AI가 도구를 37번 오가며 131초 동안 조사. 주장 8개 중 SQL 재실행으로 **8개 재현됨**.

## 요약

시험3(session_id=3, 24061행)의 품질 지표는 모두 SQL로 다시 계산해 일치했다. 누락률 10.617%(빠진 샘플 2858), 깨진 행 107, MCU 재시작 4번(행 17710, 19248, 19712, 23397), 멈춘 구간 1번(행 556→557, 4659 ms), 부하 구간 bms_current/inv_dc_current 중앙값 0.7959이다. 지표에 잡히지 않는 이상은 직접 찾아 두 가지를 확인했다. (1) 행 15010–15309(300행): 메인 접촉기가 닫혀 있는데 인버터 전압이 팩 전압보다 평균 23.8 V 낮다. 이 차이는 전류 0.7 A일 때 갑자기 생기고 86 A일 때 사라지므로 부하로는 설명되지 않는다. 같은 세션의 저전류 행에서는 팩−인버터 전압 차가 평균 −5.5 V다. 이 구간에는 value_flag 표시가 0건이다. (2) bms_charge(충전 상태 신호)가 세 세션 모두 전 구간에서 0이다. 이 신호는 기록되지 않은 것으로 보인다. 또 품질 지표의 프리차지 미달 1건이 일어난 위치를 행 1803–1889로 특정했다. 접촉기가 닫힌 뒤 인버터 전압이 0 V에서 223.7 V까지 계단식으로 오르고, 팩 전압(276 V)의 90%에 못 미치는 행이 87행이다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 10.617036294067388
- broken_timestamp_rows: 60
- mcu_restarts: 4
- pack_to_inverter_ratio_median: 0.79585326953748

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률 10.617%** 분석 규칙 3번으로 계산하면 빠진 샘플이 2858개이고, 누락률은 2858/(24061+2858)*100 = 10.617%다. 경고 기준 8%를 넘는다. | 10.617036294067388 | 10.617036294067388 | 재현됨 | 1~24061 |
| 2 | **MCU 재시작 4번** bad_ms 행을 빼고 보면 stm_ms가 앞 행보다 작아지는 곳이 4곳이다(행 17710, 19248, 19712, 23397). 행 19248부터는 메인 접촉기가 열리고 인버터 전압이 0이 된다. | 4 | 4 | 재현됨 | 17710~23397 |
| 3 | **깨진 행 107개(시각 깨짐 60개 포함)** sample_flags에서 bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행이 107개(전체의 0.445%)이고, 그중 bad_ms 행이 60개다. | 107 | 107 | 재현됨 |  |
| 4 | **부하 구간 팩/인버터 전류비 중앙값 0.7959** 부하 구간(inv_dc_current>25 A, bad_inv·bad_bms 행 제외) 5964행에서 bms_current/inv_dc_current의 중앙값은 0.79585다. 보정 계수 1.25가 필요한 근거와 맞는다. | 0.79585326953748 | 0.79585326953748 | 재현됨 |  |
| 5 | **[지표 밖] 행 15010–15309 인버터 전압이 25 V 낮게 어긋남** 행 15010에서 전류가 0.7 A인데도 인버터 전압이 275.0 V에서 250.0 V로 떨어진다. 이후 행 15309까지 300행 동안 팩 전압보다 평균 23.8 V(최소 18.3 V) 낮다. 행 15310에서 전류가 86 A로 커졌는데도 전압은 264.3 V로 되돌아온다. 같은 세션에서 접촉기가 닫혀 있고 |전류|<5 A인 다른 행들은 팩−인버터 차가 평균 −5.5 V다. 그러므로 부하로는 설명되지 않는 전압 측정 어긋남이다. 이 구간에는 value_flag 표시가 0건이라 품질 지표에 잡히지 않는다. | 23.836666666666666 | 23.836666666666666 | 재현됨 | 15010~15309 |
| 6 | **[지표 밖] 비교 기준: 그 밖의 저전류 구간 전압차 −5.5 V** 행 15010–15309와 프리차지 구간을 빼고, 접촉기가 닫혀 있고 |inv_dc_current|<5 A인 행에서 팩−인버터 전압차는 평균 −5.469 V다(인버터 전압이 조금 높음). | -5.469003582841098 | -5.469003582841098 | 재현됨 | 1890~19247 |
| 7 | **프리차지 미달 위치: 행 1803–1889** 행 1792에서 접촉기가 열렸다가 행 1803에서 다시 닫힐 때 인버터 전압은 0 V다(motor_precharge=0). 이후 행 1889까지 87, 119.2, … 223.7 V로 계단식으로 오르고, 행 1890에서 280 V가 된다. 이 87행이 팩 전압(276 V)의 90%에 못 미친다. | 87 | 87 | 재현됨 | 1803~1889 |
| 8 | **[지표 밖] bms_charge 신호가 전 구간 0** 시험3의 24061행 모두에서 bms_charge=0이다(시험1·시험2도 전 행 0). 같은 시간에 bms_capacity는 198–220 사이에서 변하므로 충전 상태 신호가 기록되지 않은 것이다. | 24061 | 24061 | 재현됨 | 1~24061 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) pm, LAG(row_no) OVER (ORDER BY row_no) pr FROM sample_flags WHERE session_id=3 AND bad_ms=0), d AS (SELECT row_no, pr, stm_ms-pm d FROM g WHERE pm IS NOT NULL), m AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-(row_no-pr-1),0) ELSE 0 END) miss FROM d) SELECT miss*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=3)+miss) FROM m`
2. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) d FROM sample_flags WHERE session_id=3 AND bad_ms=0) SELECT COUNT(*), group_concat(row_no) FROM g WHERE d<0`
3. `SELECT (SELECT COUNT(*) FROM sample_flags WHERE session_id=3 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)) broken, (SELECT COUNT(*) FROM sample_flags WHERE session_id=3 AND bad_ms=1) bad_ms`
4. `SELECT (SELECT AVG(r) FROM (SELECT bms_current/inv_dc_current r FROM sample_flags WHERE session_id=3 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0 ORDER BY r LIMIT 2 - (SELECT COUNT(*) FROM sample_flags WHERE session_id=3 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0)%2 OFFSET ((SELECT COUNT(*) FROM sample_flags WHERE session_id=3 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0)-1)/2)) med, (SELECT COUNT(*) FROM sample_flags WHERE session_id=3 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0) n`
5. `SELECT AVG(bms_voltage-inv_voltage), COUNT(*), MIN(bms_voltage-inv_voltage) FROM sample WHERE session_id=3 AND row_no BETWEEN 15010 AND 15309`
6. `SELECT AVG(bms_voltage-inv_voltage) FROM sample WHERE session_id=3 AND motor_main_contactor=1 AND row_no>1889 AND ABS(inv_dc_current)<5 AND row_no NOT BETWEEN 15010 AND 15309`
7. `SELECT COUNT(*) FROM sample WHERE session_id=3 AND row_no BETWEEN 1803 AND 1890 AND motor_main_contactor=1 AND inv_voltage < 0.9*bms_voltage`
8. `SELECT SUM(bms_charge=0), COUNT(*) FROM sample WHERE session_id=3`
