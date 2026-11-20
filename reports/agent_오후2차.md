# 분석 에이전트 보고서: 오후2차

AI가 도구를 23번 오가며 97초 동안 조사. 주장 7개 중 SQL 재실행으로 **7개 재현됨**.

## 요약

세션 '오후2차'(session_id=2, 32,710행)를 분석 규칙 v6에 따라 확인했다. stm_ms가 깨진 행(bad_ms)은 0개, 기록이 멈춘 구간은 0번, MCU 재시작(d<0)도 0번이었다. 빠진 샘플은 1,815개로 누락률은 5.2570601013758145%다. session_quality는 이 값을 5.3으로 반올림해 보여 준다. 깨진 행은 10개이고, 부하 구간 7,249행에서 bms_current/inv_dc_current 비율의 중앙값은 0.7953321364452423이다. 품질 지표에 잡히지 않는 이상은 세 가지를 찾았다. (1) row 11614~11701의 88행: 메인 컨택터가 1인데 인버터 전압이 팩 전압의 90%에 못 미친다. 같은 시간에 motor_precharge 값은 세션 전체에서 한 번도 1이 아니다. (2) row 16648~16661의 14행: 인버터 전류는 28.6 A로 부하인데 팩 전류는 0~0.1 A다. 그중 16653~16661의 9행은 토크 피드백이 음수로 바뀌었는데도 inv_dc_current가 28.6 A로 멈춰 있다. (3) row 26013~26027의 15행: 팩 전류는 29.5~30.4 A인데 인버터 전류는 1.9 A로 멈춰 있다. 주행 중(속도 10 km/h 초과)에 같은 값이 이어진 구간은 대부분 50행 안팎이다. 이 정도로는 이상이라고 단정할 수 없어 결과에 넣지 않았다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 5.2570601013758145
- broken_timestamp_rows: 0
- mcu_restarts: 0
- pack_to_inverter_ratio_median: 0.7953321364452423

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **누락률** bad_ms 행이 없는 상태에서 15<d<=1000 ms 간격으로 계산하면 빠진 샘플은 1,815개, 누락률은 5.2570601013758145%다. 멈춘 구간(d>1000)과 MCU 재시작(d<0)은 각각 0번이다. | 5.2570601013758145 | 5.2570601013758145 | 재현됨 |  |
| 2 | **깨진 행 수** bad_ms·bad_inv·bad_bms·bad_speed·bad_value 중 하나라도 1인 행은 10개다. 행 손상(n_bad_cols>=3)은 없다. | 10 | 10 | 재현됨 |  |
| 3 | **팩/인버터 전류 비율 중앙값** 부하 구간(inv_dc_current>25 A, bad_inv·bad_bms 행 제외, 7,249행)에서 보정 전 bms_current/inv_dc_current 비율의 중앙값은 0.7953321364452423이다. | 0.7953321364452423 | 0.7953321364452423 | 재현됨 |  |
| 4 | **프리차지 없이 메인 컨택터 ON, 인버터 전압 미달** row 11614에서 motor_main_contactor가 1로 바뀌었다. 그 뒤 88행 동안 inv_voltage는 45.6 V에서 227.8 V까지 오르는 중이었고, 팩 전압 281.7 V의 90%에 못 미쳤다. 같은 시간에 motor_precharge는 0이며, 이 세션에서 motor_precharge=1인 행은 하나도 없다. 컨택터 상태와 전압, 프리차지 신호가 서로 맞지 않는다. | 88 | 88 | 재현됨 | 11614~11701 |
| 5 | **인버터 부하 중 팩 전류 0** row 16648~16661의 14행에서 inv_dc_current는 28.6 A(부하)인데 bms_current는 0.0~0.1 A다. 바로 앞 행(16647)의 bms_current는 22.9 A였다. 이 중 16653~16661의 9행은 inv_torque_feedback이 -1.4로 음수인데도 inv_dc_current가 28.6 A 그대로 멈춰 있어, 두 신호가 서로 모순된다. | 14 | 14 | 재현됨 | 16648~16661 |
| 6 | **토크 음수인데 인버터 전류 28.6 A 고정** row 16653~16661의 9행에서 inv_torque_feedback은 음수(-1.4)인데 inv_dc_current는 28.6 A 부하 값에 멈춰 있다. | 9 | 9 | 재현됨 | 16653~16661 |
| 7 | **팩 전류 30 A인데 인버터 전류 1.9 A 고정** row 26013~26027의 15행에서 bms_current는 29.5~30.4 A인데 inv_dc_current는 1.9 A, 속도는 17.831 km/h로 바뀌지 않는다. row 26028에서 inv_dc_current가 37.7 A로 갱신된다. 인버터 신호가 멈춘 채 팩 전류와 모순되는 구간이다. | 15 | 15 | 재현됨 | 26013~26027 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) pm, LAG(row_no) OVER (ORDER BY row_no) pr FROM sample_flags WHERE session_id=2 AND bad_ms=0), m AS (SELECT SUM(CASE WHEN stm_ms-pm>15 AND stm_ms-pm<=1000 THEN MAX(ROUND((stm_ms-pm)/10.0)-1-(row_no-pr-1),0) ELSE 0 END) miss FROM g) SELECT miss*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=2)+miss) FROM m`
2. `SELECT COUNT(*) FROM sample_flags WHERE session_id=2 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
3. `WITH r AS (SELECT bms_current*1.0/inv_dc_current x, ROW_NUMBER() OVER (ORDER BY bms_current*1.0/inv_dc_current) rn, COUNT(*) OVER () n FROM sample_flags WHERE session_id=2 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0) SELECT AVG(x) FROM r WHERE rn IN ((n+1)/2,(n+2)/2)`
4. `SELECT COUNT(*) FROM sample WHERE session_id=2 AND motor_main_contactor=1 AND inv_voltage<0.9*bms_voltage AND row_no BETWEEN 11614 AND 11701`
5. `SELECT COUNT(*) FROM sample WHERE session_id=2 AND row_no BETWEEN 16648 AND 16661 AND inv_dc_current>25 AND ABS(bms_current)<2`
6. `SELECT COUNT(*) FROM sample WHERE session_id=2 AND row_no BETWEEN 16653 AND 16661 AND inv_dc_current>25 AND inv_torque_feedback<0`
7. `SELECT COUNT(*) FROM sample WHERE session_id=2 AND row_no BETWEEN 26013 AND 26027 AND ABS(bms_current)>20 AND ABS(inv_dc_current)<2`
