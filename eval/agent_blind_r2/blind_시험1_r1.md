# 분석 에이전트 보고서: 시험1

AI가 도구를 29번 오가며 109초 동안 조사. 주장 6개 중 SQL 재실행으로 **6개 재현됨**.

## 요약

세션 '시험1'(session_id=1, 16854행)을 조사했다. 품질 지표 결과: 누락률 10.265147481631349%(빠진 샘플 1928개)로 경고 기준 8%를 넘는다. 깨진 행은 105개(0.623%)이고, MCU 재시작은 2번(row 6071, 16067), 멈춘 구간도 2번이다. 부하 구간의 bms_current/inv_dc_current 비율 중앙값은 0.7921146953405018로, 4286행에서 계산했다. 품질 지표에 없는 이상도 하나 찾았다. bms_capacity 값이 row 1~7971(7971행)에서는 2~3에 머물다가, 43960 ms 동안 기록이 끊긴 직후인 row 7972부터 254로 뛴다. 그 뒤 row 16854까지는 242까지 1씩 줄어든다. 시험2(232~242)와 시험3(198~220)에서는 이런 낮은 값이 나오지 않았다. 따라서 row 1~7971 구간의 bms_capacity 값은 다른 구간과 같은 기준으로 비교하기 어렵다. 이 구간의 원인(BMS 초기화, 바이트 해석 오류 등)은 도구로 확인하지 못했다. 그 밖에 조향각·가속도 값이 멈춘 구간, ts_utc 역행, 바퀴 속도 0 구간도 확인했지만 뚜렷한 이상은 없었다. bms_charge 값은 세 세션 모두 늘 0이었다.

## 핵심 지표 (AI가 낸 값)

- missing_rate_pct: 10.265147481631349
- broken_timestamp_rows: 60
- mcu_restarts: 2
- pack_to_inverter_ratio_median: 0.7921146953405018

## 발견

| # | 내용 | AI 값 | 다시 계산 | 판정 | 행 범위 |
|--|--|--|--|--|--|
| 1 | **샘플 누락률 10.27%** 규칙 3에 따라 계산한 빠진 샘플은 1928개다. 누락률은 1928/(16854+1928)*100 = 10.265147481631349%로 경고 기준 8%를 넘는다. | 10.265147481631349 | 10.265147481631349 | 재현됨 |  |
| 2 | **깨진 행 105개** bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1인 행이 105개로 전체의 0.623%이고, 기준 0.05%를 넘는다. 시각이 깨진 행이 60개, 값이 튄 행이 45개이며, 행 손상은 0개다. | 105 | 105 | 재현됨 |  |
| 3 | **MCU 재시작 2번** bad_ms 행을 뺀 뒤 앞 행과의 stm_ms 차이가 음수인 곳이 2곳이다. row 6071(차이 -242113 ms)과 row 16067(차이 -144856 ms)에서 재시작했다. | 2 | 2 | 재현됨 | 6071~16067 |
| 4 | **부하 구간 팩/인버터 전류 비율 중앙값 0.792** 부하 구간(inv_dc_current>25 A, bad_inv·bad_bms 행 제외) 4286행에서 bms_current/inv_dc_current 비율의 중앙값은 0.7921146953405018이다. 보정 계수 1.25의 근거와 맞는 값이다. | 0.7921146953405018 | 0.7921146953405018 | 재현됨 |  |
| 5 | **(지표 밖) row 1~7971 bms_capacity 비정상 저값** bms_capacity 값이 row 1~7971(7971행)에서는 최대 3이다(row 1~7791은 2, 7792~7971은 3). row 7972부터 16854까지는 254에서 242로 차례로 줄어든다. 시험2(232~242)와 시험3(198~220)에는 이런 낮은 값이 없다. 품질 지표와 깨진 값 표시 어디에도 잡히지 않은 이상이다. | 3 | 3.0 | 재현됨 | 1~7971 |
| 6 | **(지표 밖) bms_capacity 급변이 43.96초 기록 끊김과 겹침** bms_capacity가 3에서 254로 바뀌는 row 7971→7972 사이에서 stm_ms 간격이 43960 ms다. 멈춘 구간 2번 가운데 한 번이 이곳이고, 기록이 다시 시작된 뒤부터 bms_capacity가 정상 범위의 값으로 나온다. | 43960 | 43960 | 재현됨 | 7971~7972 |

## 근거 SQL

1. `WITH g AS (SELECT row_no, stm_ms, LAG(stm_ms) OVER (ORDER BY row_no) pm, LAG(row_no) OVER (ORDER BY row_no) pr FROM sample_flags WHERE session_id=1 AND bad_ms=0), d AS (SELECT stm_ms-pm d, row_no-pr-1 nb FROM g WHERE pm IS NOT NULL), m AS (SELECT SUM(CASE WHEN d>15 AND d<=1000 THEN MAX(ROUND(d/10.0)-1-nb,0) ELSE 0 END) miss FROM d) SELECT miss*100.0/((SELECT COUNT(*) FROM sample WHERE session_id=1)+miss) FROM m`
2. `SELECT COUNT(*) FROM sample_flags WHERE session_id=1 AND (bad_ms=1 OR bad_inv=1 OR bad_bms=1 OR bad_speed=1 OR bad_value=1)`
3. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) d FROM sample_flags WHERE session_id=1 AND bad_ms=0) SELECT COUNT(*), MIN(row_no), MAX(row_no) FROM g WHERE d<0`
4. `WITH r AS (SELECT bms_current*1.0/inv_dc_current x FROM sample_flags WHERE session_id=1 AND inv_dc_current>25 AND bad_inv=0 AND bad_bms=0), o AS (SELECT x, ROW_NUMBER() OVER (ORDER BY x) rn, COUNT(*) OVER () c FROM r) SELECT AVG(x), MAX(c) FROM o WHERE rn IN ((c+1)/2, (c+2)/2)`
5. `SELECT MAX(bms_capacity), COUNT(*), MIN(row_no), MAX(row_no) FROM sample WHERE session_id=1 AND bms_capacity < 100`
6. `WITH g AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) d FROM sample_flags WHERE session_id=1 AND bad_ms=0) SELECT d, row_no FROM g WHERE row_no=7972`
