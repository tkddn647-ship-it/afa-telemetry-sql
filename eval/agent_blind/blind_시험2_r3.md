# 분석 에이전트 보고서: 시험2

AI가 도구를 39번 오가며 134초 동안 조사. 주장 10개 중 SQL 재실행으로 **10개 재현됨**.

## 요약

세션 '시험2'(32,576행)를 조사했다. 품질 지표를 SQL로 다시 계산했고 값이 모두 같았다. 누락률은 5.6451846488052135%(빠진 샘플 1,949개)로 기준 8%보다 낮다. 깨진 행은 105개(0.3223%)로 기준 0.05%를 넘어 경고 대상이다. MCU 재시작은 2번(row 12093, 18233)이고 기록이 멈춘 구간은 없다. 부하 구간에서 bms_current/inv_dc_current 비율의 중앙값은 0.7985611510791366이다. 지표에 안 잡히는 이상은 세 가지다. ① 팩 SOC(bms_charge)가 1~32576행 전체에서 0이다. 시험1·시험3도 모두 0이며 value_flag에도 기록되지 않는다. ② 모터 온도(inv_temp_motor)가 row 26666~26761(96행)에서 44.7로, row 27384~27431(48행)에서 38.3으로 앞뒤 값(약 41.5~42.0)에서 3°C 넘게 벗어난 채 유지된다. 이 값은 튐 판정 최소 편차 2.3을 넘지만 value_flag에 inv_temp_motor 기록이 0건이다. ③ 두 번째 MCU 재시작(row 18233)은 차량 속도 22.611 km/h로 주행하던 중에 일어났다. 메인 접촉기가 닫혀 있는데 인버터 전압이 팩 전압의 90%보다 낮은 행이 11566~11653(88행)에 있다. 이는 지표 '프리차지_미달'과 같은 사건으로 보이며, 구간 행 번호를 함께 적었다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 5.6451846488052135
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.7985611510791366

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률** 규칙 3대로 bad_ms 행을 빼고 stm_ms 간격으로 계산하면 빠진 샘플은 1,949개, 누락률은 5.6451846488052135%다. 경고 기준 8%보다 낮다. | 5.6451846488052135 | 5.6451846488052135 | 재현됨 |  |
| 2 | **깨진 행 105개 (0.3223%)** bad_ms 60, bad_inv 15, bad_bms 15, bad_speed 15, bad_value 45가 겹친 깨진 행은 105개로, 전체 행의 0.3223231827111984%다. 경고 기준 0.05%를 넘는다. | 105 | 105 | 재현됨 |  |
| 3 | **시각(stm_ms) 깨진 행 60개** sample_flags에서 bad_ms = 1인 행은 60개다. | 60 | 60 | 재현됨 |  |
| 4 | **MCU 재시작 2번** bad_ms 행을 빼고 보면 앞 행보다 stm_ms가 줄어드는 곳이 row 12093(264372→52900)과 row 18233(118270→39266) 두 곳이다. 기록이 멈춘 구간(d>1000)은 없다. | 2 | 2 | 재현됨 | 12093~18233 |
| 5 | **팩/인버터 전류 비율 중앙값** 부하 구간(inv_dc_current > 25 A, bad_inv·bad_bms 행 제외, 7,217행)에서 bms_current/inv_dc_current 비율의 중앙값은 0.7985611510791366이다. 보정 계수 1.25의 근거(약 0.80)와 맞는다. | 0.7985611510791366 | 0.7985611510791366 | 재현됨 |  |
| 6 | **[지표 밖] 팩 SOC(bms_charge)가 세션 전체에서 0** bms_charge는 1~32576행 모두 0이다. 신호가 죽어 있거나 매핑이 빠진 것으로 보인다. 값이 일정해서 value_flag에도 기록이 0건이라 품질 지표에는 드러나지 않는다. 시험1·시험3도 모든 행이 0이다. | 32576 | 32576 | 재현됨 | 1~32576 |
| 7 | **[지표 밖] 모터 온도가 38.3으로 떨어진 채 48행 유지** inv_temp_motor가 41.6(앞)에서 38.3으로 떨어져 row 27384~27431(48행) 동안 유지되다가 41.9로 돌아온다. 변화 폭이 3.3°C로 value_check의 최소 편차 2.3을 넘지만, value_flag에는 inv_temp_motor 기록이 0건이라 튐으로 잡히지 않았다. | 48 | 48 | 재현됨 | 27384~27431 |
| 8 | **[지표 밖] 모터 온도가 44.7로 튄 채 96행 유지** inv_temp_motor가 41.5(앞)에서 44.7로 올라 row 26666~26761(96행) 동안 유지되다가 42.0으로 내려온다. 앞뒤 값과의 차이(3.2, 2.7)가 최소 편차 2.3을 넘지만 value_flag에는 기록이 없다. | 96 | 96 | 재현됨 | 26666~26761 |
| 9 | **[지표 밖] 두 번째 MCU 재시작은 주행 중** row 18233의 MCU 재시작 때 차량 속도는 22.611 km/h였다(stm_ms 118270→39266). 정차 중이 아니라 주행 중에 재시작했다. row 12093의 재시작 직전 속도는 0.089 km/h였다. | 22.611 | 22.611 | 재현됨 | 18233~18233 |
| 10 | **접촉기 닫힘 중 인버터 전압 미달 구간** motor_main_contactor = 1인데 inv_voltage가 bms_voltage의 90%보다 낮은 행이 row 11566~11653에 88행 있다. 최소 전압비는 0.162로, 지표 '닫힐때_전압비_최소' 0.162와 같다. 지표 '프리차지_미달 1'과 같은 사건으로 보이며, 해당 행 범위를 함께 적었다. | 88 | 88 | 재현됨 | 11566~11653 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms FROM sample_flags WHERE session_id=2 AND bad_ms=0), d AS (SELECT stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) AS d, row_no - LAG(row_no) OVER (ORDER BY row_no) - 1 AS nb FROM g), m AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) AS miss FROM d) SELECT miss*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=2)+miss) AS missing_rate_pct, miss FROM m`
2. `SELECT COUNT(*) AS broken, COUNT(*)*100.0/(SELECT COUNT(*) FROM sample WHERE session_id=2) AS pct FROM sample_flags WHERE session_id=2 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
3. `SELECT COUNT(*) FROM sample_flags WHERE session_id=2 AND bad_ms=1`
4. `WITH g AS (SELECT row_no, stm_ms FROM sample_flags WHERE session_id=2 AND bad_ms=0), d AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) AS d FROM g) SELECT COUNT(*) AS restarts, MIN(row_no), MAX(row_no) FROM d WHERE d<0`
5. `WITH r AS (SELECT bms_current*1.0/inv_dc_current AS x, ROW_NUMBER() OVER (ORDER BY bms_current*1.0/inv_dc_current) AS rn, COUNT(*) OVER () AS n FROM sample_flags WHERE session_id=2 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0) SELECT AVG(x) AS median, MAX(n) FROM r WHERE rn IN ((n+1)/2,(n+2)/2)`
6. `SELECT COUNT(*) AS rows_soc_zero, MIN(row_no), MAX(row_no), (SELECT COUNT(*) FROM value_flag WHERE session_id=2 AND column_name='bms_charge') AS flagged FROM sample WHERE session_id=2 AND bms_charge=0`
7. `SELECT COUNT(*) AS n, MIN(row_no), MAX(row_no), MIN(inv_temp_motor), MAX(inv_temp_motor) FROM sample WHERE session_id=2 AND row_no BETWEEN 27384 AND 27431 AND inv_temp_motor=38.3`
8. `SELECT COUNT(*) AS n, MIN(row_no), MAX(row_no) FROM sample WHERE session_id=2 AND row_no BETWEEN 26666 AND 26761 AND inv_temp_motor=44.7`
9. `SELECT vehicle_speed_kmh, stm_ms, (SELECT stm_ms FROM sample WHERE session_id=2 AND row_no=18232) AS prev_stm FROM sample WHERE session_id=2 AND row_no=18233`
10. `SELECT COUNT(*) AS n, MIN(row_no), MAX(row_no), MIN(inv_voltage/bms_voltage) FROM sample WHERE session_id=2 AND motor_main_contactor=1 AND inv_voltage < 0.9*bms_voltage`
