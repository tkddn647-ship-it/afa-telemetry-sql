# 결함 목록

`python trace.py`가 요구사항 추적표에서 실패한 칸마다 만든 목록. 재현 SQL을 그대로 실행하면 같은 결과가 나온다.

## DEF-01 [REQ-02] MCU 시각이 깨진 행은 0.05% 이하 — 오후6차

- 기대: 깨진 시각 행 / 전체 행 ≤ 0.05%
- 관찰: 0.054%
- 근거: 데이터 품질 (시리얼 전송 중 숫자가 빠지거나 끼어듦)
- 상태: 열림 (원인 미확인)
- 재현:

```sql
SELECT row_no, stm_ms FROM sample_flags JOIN session USING (session_id) WHERE label = '오후6차' AND bad_ms;
```

## DEF-02 [REQ-02] MCU 시각이 깨진 행은 0.05% 이하 — 오후7차

- 기대: 깨진 시각 행 / 전체 행 ≤ 0.05%
- 관찰: 0.079%
- 근거: 데이터 품질 (시리얼 전송 중 숫자가 빠지거나 끼어듦)
- 상태: 열림 (원인 미확인)
- 재현:

```sql
SELECT row_no, stm_ms FROM sample_flags JOIN session USING (session_id) WHERE label = '오후7차' AND bad_ms;
```

## DEF-03 [REQ-03] 샘플 누락률 8% 이하 — 오후1차

- 기대: 누락률 ≤ 8%
- 관찰: 9.1%
- 근거: 계측 주기 10 ms, 분석에 필요한 최소 밀도
- 상태: 열림 (원인 미확인)
- 재현:

```sql
sql/06_sample_loss.sql
```

## DEF-04 [REQ-03] 샘플 누락률 8% 이하 — 오후6차

- 기대: 누락률 ≤ 8%
- 관찰: 9.8%
- 근거: 계측 주기 10 ms, 분석에 필요한 최소 밀도
- 상태: 열림 (원인 미확인)
- 재현:

```sql
sql/06_sample_loss.sql
```

## DEF-05 [REQ-03] 샘플 누락률 8% 이하 — 092619_465091_동_오후6시1차

- 기대: 누락률 ≤ 8%
- 관찰: 8.3%
- 근거: 계측 주기 10 ms, 분석에 필요한 최소 밀도
- 상태: 열림 (원인 미확인)
- 재현:

```sql
sql/06_sample_loss.sql
```

## DEF-06 [REQ-03] 샘플 누락률 8% 이하 — 오후7차

- 기대: 누락률 ≤ 8%
- 관찰: 12.5%
- 근거: 계측 주기 10 ms, 분석에 필요한 최소 밀도
- 상태: 열림 (원인 미확인)
- 재현:

```sql
sql/06_sample_loss.sql
```

## DEF-07 [REQ-04] 주행 중 MCU 재시작 없음 — 오후6차

- 기대: 재시작 0회
- 관찰: 2회
- 근거: 계측 연속성 (재시작하면 시계가 0부터 다시 셈)
- 상태: 열림 (원인 미확인)
- 재현:

```sql
WITH c AS (SELECT row_no, stm_ms - LAG(stm_ms) OVER (ORDER BY row_no) d FROM sample_flags JOIN session USING (session_id) WHERE label = '오후6차' AND NOT bad_ms) SELECT row_no, d FROM c WHERE d < 0;
```

## DEF-08 [REQ-05] 팩 전류 신호의 배율이 맞다 (원본) — 오후1차

- 기대: 부하 구간 팩/인버터 비율 중앙값 0.95~1.05
- 관찰: 0.801
- 근거: 물리 기준 - 인버터는 배터리에서 전류를 받으므로 부하 구간 팩/인버터 비율 ≈ 1
- 상태: 원인 규명: BMS 전류 CAN 신호의 스케일 계수 누락. 조치: 보정 계수 1.25 (REQ-06에서 확인).
- 재현:

```sql
WITH r AS (SELECT bms_current / inv_dc_current AS v, ROW_NUMBER() OVER (ORDER BY bms_current / inv_dc_current) rn, COUNT(*) OVER () n FROM sample_flags f JOIN session USING (session_id) CROSS JOIN (SELECT factor k FROM scale_correction WHERE column_name='bms_current') WHERE label = '오후1차' AND inv_dc_current > 25 AND NOT bad_inv AND NOT bad_bms) SELECT AVG(v) FROM r WHERE rn IN ((n+1)/2, (n+2)/2);
```

## DEF-09 [REQ-05] 팩 전류 신호의 배율이 맞다 (원본) — 오후2차

- 기대: 부하 구간 팩/인버터 비율 중앙값 0.95~1.05
- 관찰: 0.795
- 근거: 물리 기준 - 인버터는 배터리에서 전류를 받으므로 부하 구간 팩/인버터 비율 ≈ 1
- 상태: 원인 규명: BMS 전류 CAN 신호의 스케일 계수 누락. 조치: 보정 계수 1.25 (REQ-06에서 확인).
- 재현:

```sql
WITH r AS (SELECT bms_current / inv_dc_current AS v, ROW_NUMBER() OVER (ORDER BY bms_current / inv_dc_current) rn, COUNT(*) OVER () n FROM sample_flags f JOIN session USING (session_id) CROSS JOIN (SELECT factor k FROM scale_correction WHERE column_name='bms_current') WHERE label = '오후2차' AND inv_dc_current > 25 AND NOT bad_inv AND NOT bad_bms) SELECT AVG(v) FROM r WHERE rn IN ((n+1)/2, (n+2)/2);
```

## DEF-10 [REQ-05] 팩 전류 신호의 배율이 맞다 (원본) — 오후6차

- 기대: 부하 구간 팩/인버터 비율 중앙값 0.95~1.05
- 관찰: 0.796
- 근거: 물리 기준 - 인버터는 배터리에서 전류를 받으므로 부하 구간 팩/인버터 비율 ≈ 1
- 상태: 원인 규명: BMS 전류 CAN 신호의 스케일 계수 누락. 조치: 보정 계수 1.25 (REQ-06에서 확인).
- 재현:

```sql
WITH r AS (SELECT bms_current / inv_dc_current AS v, ROW_NUMBER() OVER (ORDER BY bms_current / inv_dc_current) rn, COUNT(*) OVER () n FROM sample_flags f JOIN session USING (session_id) CROSS JOIN (SELECT factor k FROM scale_correction WHERE column_name='bms_current') WHERE label = '오후6차' AND inv_dc_current > 25 AND NOT bad_inv AND NOT bad_bms) SELECT AVG(v) FROM r WHERE rn IN ((n+1)/2, (n+2)/2);
```

## DEF-11 [REQ-05] 팩 전류 신호의 배율이 맞다 (원본) — 092619_465091_동_오후6시1차

- 기대: 부하 구간 팩/인버터 비율 중앙값 0.95~1.05
- 관찰: 0.797
- 근거: 물리 기준 - 인버터는 배터리에서 전류를 받으므로 부하 구간 팩/인버터 비율 ≈ 1
- 상태: 원인 규명: BMS 전류 CAN 신호의 스케일 계수 누락. 조치: 보정 계수 1.25 (REQ-06에서 확인).
- 재현:

```sql
WITH r AS (SELECT bms_current / inv_dc_current AS v, ROW_NUMBER() OVER (ORDER BY bms_current / inv_dc_current) rn, COUNT(*) OVER () n FROM sample_flags f JOIN session USING (session_id) CROSS JOIN (SELECT factor k FROM scale_correction WHERE column_name='bms_current') WHERE label = '092619_465091_동_오후6시1차' AND inv_dc_current > 25 AND NOT bad_inv AND NOT bad_bms) SELECT AVG(v) FROM r WHERE rn IN ((n+1)/2, (n+2)/2);
```

## DEF-12 [REQ-05] 팩 전류 신호의 배율이 맞다 (원본) — 오전2차

- 기대: 부하 구간 팩/인버터 비율 중앙값 0.95~1.05
- 관찰: 0.795
- 근거: 물리 기준 - 인버터는 배터리에서 전류를 받으므로 부하 구간 팩/인버터 비율 ≈ 1
- 상태: 원인 규명: BMS 전류 CAN 신호의 스케일 계수 누락. 조치: 보정 계수 1.25 (REQ-06에서 확인).
- 재현:

```sql
WITH r AS (SELECT bms_current / inv_dc_current AS v, ROW_NUMBER() OVER (ORDER BY bms_current / inv_dc_current) rn, COUNT(*) OVER () n FROM sample_flags f JOIN session USING (session_id) CROSS JOIN (SELECT factor k FROM scale_correction WHERE column_name='bms_current') WHERE label = '오전2차' AND inv_dc_current > 25 AND NOT bad_inv AND NOT bad_bms) SELECT AVG(v) FROM r WHERE rn IN ((n+1)/2, (n+2)/2);
```

## DEF-13 [REQ-05] 팩 전류 신호의 배율이 맞다 (원본) — 오전_1차

- 기대: 부하 구간 팩/인버터 비율 중앙값 0.95~1.05
- 관찰: 0.805
- 근거: 물리 기준 - 인버터는 배터리에서 전류를 받으므로 부하 구간 팩/인버터 비율 ≈ 1
- 상태: 원인 규명: BMS 전류 CAN 신호의 스케일 계수 누락. 조치: 보정 계수 1.25 (REQ-06에서 확인).
- 재현:

```sql
WITH r AS (SELECT bms_current / inv_dc_current AS v, ROW_NUMBER() OVER (ORDER BY bms_current / inv_dc_current) rn, COUNT(*) OVER () n FROM sample_flags f JOIN session USING (session_id) CROSS JOIN (SELECT factor k FROM scale_correction WHERE column_name='bms_current') WHERE label = '오전_1차' AND inv_dc_current > 25 AND NOT bad_inv AND NOT bad_bms) SELECT AVG(v) FROM r WHERE rn IN ((n+1)/2, (n+2)/2);
```

## DEF-14 [REQ-05] 팩 전류 신호의 배율이 맞다 (원본) — 오후7차

- 기대: 부하 구간 팩/인버터 비율 중앙값 0.95~1.05
- 관찰: 0.808
- 근거: 물리 기준 - 인버터는 배터리에서 전류를 받으므로 부하 구간 팩/인버터 비율 ≈ 1
- 상태: 원인 규명: BMS 전류 CAN 신호의 스케일 계수 누락. 조치: 보정 계수 1.25 (REQ-06에서 확인).
- 재현:

```sql
WITH r AS (SELECT bms_current / inv_dc_current AS v, ROW_NUMBER() OVER (ORDER BY bms_current / inv_dc_current) rn, COUNT(*) OVER () n FROM sample_flags f JOIN session USING (session_id) CROSS JOIN (SELECT factor k FROM scale_correction WHERE column_name='bms_current') WHERE label = '오후7차' AND inv_dc_current > 25 AND NOT bad_inv AND NOT bad_bms) SELECT AVG(v) FROM r WHERE rn IN ((n+1)/2, (n+2)/2);
```

## DEF-15 [REQ-07] 보정 뒤 물리 기준 위반 30% 이하 — 오후6차

- 기대: 인버터 > 보정 팩×1.05 인 부하 샘플 ≤ 30%
- 관찰: 32.3%
- 근거: 물리 기준 - 팩 전류 ≥ 인버터 전류 (잡음 여유 5%)
- 상태: 열림 (원인 미확인)
- 재현:

```sql
sql/07_physics_check.sql
```

## DEF-16 [REQ-07] 보정 뒤 물리 기준 위반 30% 이하 — 092619_465091_동_오후6시1차

- 기대: 인버터 > 보정 팩×1.05 인 부하 샘플 ≤ 30%
- 관찰: 31.6%
- 근거: 물리 기준 - 팩 전류 ≥ 인버터 전류 (잡음 여유 5%)
- 상태: 열림 (원인 미확인)
- 재현:

```sql
sql/07_physics_check.sql
```
