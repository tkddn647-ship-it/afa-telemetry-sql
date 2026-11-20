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
- 관찰: 32.2%
- 근거: 물리 기준 - 팩 전류 ≥ 인버터 전류 (잡음 여유 5%)
- 상태: 열림 (원인 미확인)
- 재현:

```sql
sql/07_physics_check.sql
```

## DEF-16 [REQ-07] 보정 뒤 물리 기준 위반 30% 이하 — 092619_465091_동_오후6시1차

- 기대: 인버터 > 보정 팩×1.05 인 부하 샘플 ≤ 30%
- 관찰: 31.5%
- 근거: 물리 기준 - 팩 전류 ≥ 인버터 전류 (잡음 여유 5%)
- 상태: 열림 (원인 미확인)
- 재현:

```sql
sql/07_physics_check.sql
```

## DEF-17 [REQ-14] 메인 접촉기가 닫힐 때 프리차지가 끝나 있다 — 오후1차

- 기대: 접촉기 신호 0→1 순간 인버터 전압 ≥ 팩 전압 × 0.90
- 관찰: 닫힘 1번 중 미달 1번 (최소 16%)
- 근거: KSAE 대학생 자작자동차대회 차량기술규정(2024.11.21 시행) 제52조 ① (마지막 AIR가 닫히기 전 구동시스템 전압이 축전지 전압의 90%까지 확보. FS Rules 2026 EV5.7.1 은 95%). 인버터 DC 전압 = 차량 쪽, BMS 팩 전압 = 배터리. 깨진 행은 빼고 판정 (한 줄 손상 행은 접촉기 신호까지 0으로 채워져 가짜 닫힘을 만듦). 신호 정의 결함 — 펌웨어가 motor_main_contactor 를 VSM 상태 >= 2(초기충전 중)로 만들어, 지금 로그로는 판정할 수 없음
- 상태: 원인 규명 (2026-11-20): 신호 정의 결함이지 프리차지 위반의 근거가 아님. 펌웨어 can_vehicle.c 가 motor_main_contactor 를 인버터 VSM 상태(CAN 0x0AA 바이트 0) >= 2 로 만드는데, CAN Protocol V5.9 에서 2 = 'Pre-charge Active'. 로그의 0→1 은 초기충전 시작이고, 그 뒤 전류 0 A 로 전압이 16% → 90% 까지 약 920 ms 에 오름 (초기충전 곡선). 팀의 ESP32 코드는 3~6 을 닫힘으로 둠. 조치 제안: STM 매핑을 문서대로(3~6) 고치고 VSM 상태 값 자체를 기록. 실제 AIR 닫힘 시각이 로그에 없으므로 KSAE 제52조 ④(1초 이상 초기충전)도 지금은 판정 불가.
- 재현:

```sql
WITH c AS (SELECT row_no, motor_main_contactor mc, LAG(motor_main_contactor) OVER (ORDER BY row_no) p, inv_voltage, bms_voltage FROM sample_clean JOIN session USING (session_id) WHERE label = '오후1차') SELECT row_no, inv_voltage, bms_voltage, ROUND(inv_voltage / bms_voltage, 3) AS ratio FROM c WHERE mc = 1 AND p = 0;
```

## DEF-18 [REQ-14] 메인 접촉기가 닫힐 때 프리차지가 끝나 있다 — 오후2차

- 기대: 접촉기 신호 0→1 순간 인버터 전압 ≥ 팩 전압 × 0.90
- 관찰: 닫힘 1번 중 미달 1번 (최소 16%)
- 근거: KSAE 대학생 자작자동차대회 차량기술규정(2024.11.21 시행) 제52조 ① (마지막 AIR가 닫히기 전 구동시스템 전압이 축전지 전압의 90%까지 확보. FS Rules 2026 EV5.7.1 은 95%). 인버터 DC 전압 = 차량 쪽, BMS 팩 전압 = 배터리. 깨진 행은 빼고 판정 (한 줄 손상 행은 접촉기 신호까지 0으로 채워져 가짜 닫힘을 만듦). 신호 정의 결함 — 펌웨어가 motor_main_contactor 를 VSM 상태 >= 2(초기충전 중)로 만들어, 지금 로그로는 판정할 수 없음
- 상태: 원인 규명 (2026-11-20): 신호 정의 결함이지 프리차지 위반의 근거가 아님. 펌웨어 can_vehicle.c 가 motor_main_contactor 를 인버터 VSM 상태(CAN 0x0AA 바이트 0) >= 2 로 만드는데, CAN Protocol V5.9 에서 2 = 'Pre-charge Active'. 로그의 0→1 은 초기충전 시작이고, 그 뒤 전류 0 A 로 전압이 16% → 90% 까지 약 920 ms 에 오름 (초기충전 곡선). 팀의 ESP32 코드는 3~6 을 닫힘으로 둠. 조치 제안: STM 매핑을 문서대로(3~6) 고치고 VSM 상태 값 자체를 기록. 실제 AIR 닫힘 시각이 로그에 없으므로 KSAE 제52조 ④(1초 이상 초기충전)도 지금은 판정 불가.
- 재현:

```sql
WITH c AS (SELECT row_no, motor_main_contactor mc, LAG(motor_main_contactor) OVER (ORDER BY row_no) p, inv_voltage, bms_voltage FROM sample_clean JOIN session USING (session_id) WHERE label = '오후2차') SELECT row_no, inv_voltage, bms_voltage, ROUND(inv_voltage / bms_voltage, 3) AS ratio FROM c WHERE mc = 1 AND p = 0;
```

## DEF-19 [REQ-14] 메인 접촉기가 닫힐 때 프리차지가 끝나 있다 — 오후6차

- 기대: 접촉기 신호 0→1 순간 인버터 전압 ≥ 팩 전압 × 0.90
- 관찰: 닫힘 1번 중 미달 1번 (최소 0%)
- 근거: KSAE 대학생 자작자동차대회 차량기술규정(2024.11.21 시행) 제52조 ① (마지막 AIR가 닫히기 전 구동시스템 전압이 축전지 전압의 90%까지 확보. FS Rules 2026 EV5.7.1 은 95%). 인버터 DC 전압 = 차량 쪽, BMS 팩 전압 = 배터리. 깨진 행은 빼고 판정 (한 줄 손상 행은 접촉기 신호까지 0으로 채워져 가짜 닫힘을 만듦). 신호 정의 결함 — 펌웨어가 motor_main_contactor 를 VSM 상태 >= 2(초기충전 중)로 만들어, 지금 로그로는 판정할 수 없음
- 상태: 원인 규명 (2026-11-20): 신호 정의 결함이지 프리차지 위반의 근거가 아님. 펌웨어 can_vehicle.c 가 motor_main_contactor 를 인버터 VSM 상태(CAN 0x0AA 바이트 0) >= 2 로 만드는데, CAN Protocol V5.9 에서 2 = 'Pre-charge Active'. 로그의 0→1 은 초기충전 시작이고, 그 뒤 전류 0 A 로 전압이 16% → 90% 까지 약 920 ms 에 오름 (초기충전 곡선). 팀의 ESP32 코드는 3~6 을 닫힘으로 둠. 조치 제안: STM 매핑을 문서대로(3~6) 고치고 VSM 상태 값 자체를 기록. 실제 AIR 닫힘 시각이 로그에 없으므로 KSAE 제52조 ④(1초 이상 초기충전)도 지금은 판정 불가.
- 재현:

```sql
WITH c AS (SELECT row_no, motor_main_contactor mc, LAG(motor_main_contactor) OVER (ORDER BY row_no) p, inv_voltage, bms_voltage FROM sample_clean JOIN session USING (session_id) WHERE label = '오후6차') SELECT row_no, inv_voltage, bms_voltage, ROUND(inv_voltage / bms_voltage, 3) AS ratio FROM c WHERE mc = 1 AND p = 0;
```

## DEF-20 [REQ-14] 메인 접촉기가 닫힐 때 프리차지가 끝나 있다 — 092619_465091_동_오후6시1차

- 기대: 접촉기 신호 0→1 순간 인버터 전압 ≥ 팩 전압 × 0.90
- 관찰: 닫힘 1번 중 미달 1번 (최소 31%)
- 근거: KSAE 대학생 자작자동차대회 차량기술규정(2024.11.21 시행) 제52조 ① (마지막 AIR가 닫히기 전 구동시스템 전압이 축전지 전압의 90%까지 확보. FS Rules 2026 EV5.7.1 은 95%). 인버터 DC 전압 = 차량 쪽, BMS 팩 전압 = 배터리. 깨진 행은 빼고 판정 (한 줄 손상 행은 접촉기 신호까지 0으로 채워져 가짜 닫힘을 만듦). 신호 정의 결함 — 펌웨어가 motor_main_contactor 를 VSM 상태 >= 2(초기충전 중)로 만들어, 지금 로그로는 판정할 수 없음
- 상태: 원인 규명 (2026-11-20): 신호 정의 결함이지 프리차지 위반의 근거가 아님. 펌웨어 can_vehicle.c 가 motor_main_contactor 를 인버터 VSM 상태(CAN 0x0AA 바이트 0) >= 2 로 만드는데, CAN Protocol V5.9 에서 2 = 'Pre-charge Active'. 로그의 0→1 은 초기충전 시작이고, 그 뒤 전류 0 A 로 전압이 16% → 90% 까지 약 920 ms 에 오름 (초기충전 곡선). 팀의 ESP32 코드는 3~6 을 닫힘으로 둠. 조치 제안: STM 매핑을 문서대로(3~6) 고치고 VSM 상태 값 자체를 기록. 실제 AIR 닫힘 시각이 로그에 없으므로 KSAE 제52조 ④(1초 이상 초기충전)도 지금은 판정 불가.
- 재현:

```sql
WITH c AS (SELECT row_no, motor_main_contactor mc, LAG(motor_main_contactor) OVER (ORDER BY row_no) p, inv_voltage, bms_voltage FROM sample_clean JOIN session USING (session_id) WHERE label = '092619_465091_동_오후6시1차') SELECT row_no, inv_voltage, bms_voltage, ROUND(inv_voltage / bms_voltage, 3) AS ratio FROM c WHERE mc = 1 AND p = 0;
```

## DEF-21 [REQ-14] 메인 접촉기가 닫힐 때 프리차지가 끝나 있다 — 오전_1차

- 기대: 접촉기 신호 0→1 순간 인버터 전압 ≥ 팩 전압 × 0.90
- 관찰: 닫힘 1번 중 미달 1번 (최소 16%)
- 근거: KSAE 대학생 자작자동차대회 차량기술규정(2024.11.21 시행) 제52조 ① (마지막 AIR가 닫히기 전 구동시스템 전압이 축전지 전압의 90%까지 확보. FS Rules 2026 EV5.7.1 은 95%). 인버터 DC 전압 = 차량 쪽, BMS 팩 전압 = 배터리. 깨진 행은 빼고 판정 (한 줄 손상 행은 접촉기 신호까지 0으로 채워져 가짜 닫힘을 만듦). 신호 정의 결함 — 펌웨어가 motor_main_contactor 를 VSM 상태 >= 2(초기충전 중)로 만들어, 지금 로그로는 판정할 수 없음
- 상태: 원인 규명 (2026-11-20): 신호 정의 결함이지 프리차지 위반의 근거가 아님. 펌웨어 can_vehicle.c 가 motor_main_contactor 를 인버터 VSM 상태(CAN 0x0AA 바이트 0) >= 2 로 만드는데, CAN Protocol V5.9 에서 2 = 'Pre-charge Active'. 로그의 0→1 은 초기충전 시작이고, 그 뒤 전류 0 A 로 전압이 16% → 90% 까지 약 920 ms 에 오름 (초기충전 곡선). 팀의 ESP32 코드는 3~6 을 닫힘으로 둠. 조치 제안: STM 매핑을 문서대로(3~6) 고치고 VSM 상태 값 자체를 기록. 실제 AIR 닫힘 시각이 로그에 없으므로 KSAE 제52조 ④(1초 이상 초기충전)도 지금은 판정 불가.
- 재현:

```sql
WITH c AS (SELECT row_no, motor_main_contactor mc, LAG(motor_main_contactor) OVER (ORDER BY row_no) p, inv_voltage, bms_voltage FROM sample_clean JOIN session USING (session_id) WHERE label = '오전_1차') SELECT row_no, inv_voltage, bms_voltage, ROUND(inv_voltage / bms_voltage, 3) AS ratio FROM c WHERE mc = 1 AND p = 0;
```

## DEF-22 [REQ-14] 메인 접촉기가 닫힐 때 프리차지가 끝나 있다 — 오후7차

- 기대: 접촉기 신호 0→1 순간 인버터 전압 ≥ 팩 전압 × 0.90
- 관찰: 닫힘 1번 중 미달 1번 (최소 16%)
- 근거: KSAE 대학생 자작자동차대회 차량기술규정(2024.11.21 시행) 제52조 ① (마지막 AIR가 닫히기 전 구동시스템 전압이 축전지 전압의 90%까지 확보. FS Rules 2026 EV5.7.1 은 95%). 인버터 DC 전압 = 차량 쪽, BMS 팩 전압 = 배터리. 깨진 행은 빼고 판정 (한 줄 손상 행은 접촉기 신호까지 0으로 채워져 가짜 닫힘을 만듦). 신호 정의 결함 — 펌웨어가 motor_main_contactor 를 VSM 상태 >= 2(초기충전 중)로 만들어, 지금 로그로는 판정할 수 없음
- 상태: 원인 규명 (2026-11-20): 신호 정의 결함이지 프리차지 위반의 근거가 아님. 펌웨어 can_vehicle.c 가 motor_main_contactor 를 인버터 VSM 상태(CAN 0x0AA 바이트 0) >= 2 로 만드는데, CAN Protocol V5.9 에서 2 = 'Pre-charge Active'. 로그의 0→1 은 초기충전 시작이고, 그 뒤 전류 0 A 로 전압이 16% → 90% 까지 약 920 ms 에 오름 (초기충전 곡선). 팀의 ESP32 코드는 3~6 을 닫힘으로 둠. 조치 제안: STM 매핑을 문서대로(3~6) 고치고 VSM 상태 값 자체를 기록. 실제 AIR 닫힘 시각이 로그에 없으므로 KSAE 제52조 ④(1초 이상 초기충전)도 지금은 판정 불가.
- 재현:

```sql
WITH c AS (SELECT row_no, motor_main_contactor mc, LAG(motor_main_contactor) OVER (ORDER BY row_no) p, inv_voltage, bms_voltage FROM sample_clean JOIN session USING (session_id) WHERE label = '오후7차') SELECT row_no, inv_voltage, bms_voltage, ROUND(inv_voltage / bms_voltage, 3) AS ratio FROM c WHERE mc = 1 AND p = 0;
```

## DEF-23 [REQ-15] 부하 중 인버터 전류와 팩 전류가 한 CAN 주기 넘게 어긋나지 않는다 — 오후2차

- 기대: 10행 이상 이어진 불일치 0번
- 관찰: 1번 (가장 긴 것 14행)
- 근거: 인버터 > 25 A 인데 팩 ≤ 0.5 A. CAN 값은 약 10행(100 ms)마다 갱신되므로 그보다 짧은 불일치는 두 메시지의 갱신 시점 차이로 봄 (실제 로그 108번, 대부분 1~5행)
- 상태: 추정 (2026-11-20): 10행 넘게 이어진 불일치 11번 중 10번은 팩 전류가 내내 음수(약 -1~-3 A, 페달을 뗀 상태), 7번은 그동안 인버터 전류가 한 값으로 고정 → 부하가 갑자기 줄 때 인버터 전류 값이 갱신되지 않는 것으로 보임. 인버터 CAN 메시지 주기·지연 확인 필요. 10행 미만 불일치 108번은 두 메시지의 갱신 시점 차이로 보고 결함으로 세지 않음.
- 재현:

```sql
WITH m AS (SELECT row_no, row_no - ROW_NUMBER() OVER (ORDER BY row_no) g FROM sample_clean JOIN session USING (session_id) WHERE label = '오후2차' AND inv_dc_current > 25 AND bms_current <= 0.5) SELECT MIN(row_no) AS 시작_행, COUNT(*) AS 행_수 FROM m GROUP BY g HAVING COUNT(*) >= 10;
```

## DEF-24 [REQ-15] 부하 중 인버터 전류와 팩 전류가 한 CAN 주기 넘게 어긋나지 않는다 — 오후6차

- 기대: 10행 이상 이어진 불일치 0번
- 관찰: 5번 (가장 긴 것 13행)
- 근거: 인버터 > 25 A 인데 팩 ≤ 0.5 A. CAN 값은 약 10행(100 ms)마다 갱신되므로 그보다 짧은 불일치는 두 메시지의 갱신 시점 차이로 봄 (실제 로그 108번, 대부분 1~5행)
- 상태: 추정 (2026-11-20): 10행 넘게 이어진 불일치 11번 중 10번은 팩 전류가 내내 음수(약 -1~-3 A, 페달을 뗀 상태), 7번은 그동안 인버터 전류가 한 값으로 고정 → 부하가 갑자기 줄 때 인버터 전류 값이 갱신되지 않는 것으로 보임. 인버터 CAN 메시지 주기·지연 확인 필요. 10행 미만 불일치 108번은 두 메시지의 갱신 시점 차이로 보고 결함으로 세지 않음.
- 재현:

```sql
WITH m AS (SELECT row_no, row_no - ROW_NUMBER() OVER (ORDER BY row_no) g FROM sample_clean JOIN session USING (session_id) WHERE label = '오후6차' AND inv_dc_current > 25 AND bms_current <= 0.5) SELECT MIN(row_no) AS 시작_행, COUNT(*) AS 행_수 FROM m GROUP BY g HAVING COUNT(*) >= 10;
```

## DEF-25 [REQ-15] 부하 중 인버터 전류와 팩 전류가 한 CAN 주기 넘게 어긋나지 않는다 — 092619_465091_동_오후6시1차

- 기대: 10행 이상 이어진 불일치 0번
- 관찰: 2번 (가장 긴 것 15행)
- 근거: 인버터 > 25 A 인데 팩 ≤ 0.5 A. CAN 값은 약 10행(100 ms)마다 갱신되므로 그보다 짧은 불일치는 두 메시지의 갱신 시점 차이로 봄 (실제 로그 108번, 대부분 1~5행)
- 상태: 추정 (2026-11-20): 10행 넘게 이어진 불일치 11번 중 10번은 팩 전류가 내내 음수(약 -1~-3 A, 페달을 뗀 상태), 7번은 그동안 인버터 전류가 한 값으로 고정 → 부하가 갑자기 줄 때 인버터 전류 값이 갱신되지 않는 것으로 보임. 인버터 CAN 메시지 주기·지연 확인 필요. 10행 미만 불일치 108번은 두 메시지의 갱신 시점 차이로 보고 결함으로 세지 않음.
- 재현:

```sql
WITH m AS (SELECT row_no, row_no - ROW_NUMBER() OVER (ORDER BY row_no) g FROM sample_clean JOIN session USING (session_id) WHERE label = '092619_465091_동_오후6시1차' AND inv_dc_current > 25 AND bms_current <= 0.5) SELECT MIN(row_no) AS 시작_행, COUNT(*) AS 행_수 FROM m GROUP BY g HAVING COUNT(*) >= 10;
```

## DEF-26 [REQ-15] 부하 중 인버터 전류와 팩 전류가 한 CAN 주기 넘게 어긋나지 않는다 — 오전_1차

- 기대: 10행 이상 이어진 불일치 0번
- 관찰: 1번 (가장 긴 것 10행)
- 근거: 인버터 > 25 A 인데 팩 ≤ 0.5 A. CAN 값은 약 10행(100 ms)마다 갱신되므로 그보다 짧은 불일치는 두 메시지의 갱신 시점 차이로 봄 (실제 로그 108번, 대부분 1~5행)
- 상태: 추정 (2026-11-20): 10행 넘게 이어진 불일치 11번 중 10번은 팩 전류가 내내 음수(약 -1~-3 A, 페달을 뗀 상태), 7번은 그동안 인버터 전류가 한 값으로 고정 → 부하가 갑자기 줄 때 인버터 전류 값이 갱신되지 않는 것으로 보임. 인버터 CAN 메시지 주기·지연 확인 필요. 10행 미만 불일치 108번은 두 메시지의 갱신 시점 차이로 보고 결함으로 세지 않음.
- 재현:

```sql
WITH m AS (SELECT row_no, row_no - ROW_NUMBER() OVER (ORDER BY row_no) g FROM sample_clean JOIN session USING (session_id) WHERE label = '오전_1차' AND inv_dc_current > 25 AND bms_current <= 0.5) SELECT MIN(row_no) AS 시작_행, COUNT(*) AS 행_수 FROM m GROUP BY g HAVING COUNT(*) >= 10;
```

## DEF-27 [REQ-15] 부하 중 인버터 전류와 팩 전류가 한 CAN 주기 넘게 어긋나지 않는다 — 오후7차

- 기대: 10행 이상 이어진 불일치 0번
- 관찰: 2번 (가장 긴 것 12행)
- 근거: 인버터 > 25 A 인데 팩 ≤ 0.5 A. CAN 값은 약 10행(100 ms)마다 갱신되므로 그보다 짧은 불일치는 두 메시지의 갱신 시점 차이로 봄 (실제 로그 108번, 대부분 1~5행)
- 상태: 추정 (2026-11-20): 10행 넘게 이어진 불일치 11번 중 10번은 팩 전류가 내내 음수(약 -1~-3 A, 페달을 뗀 상태), 7번은 그동안 인버터 전류가 한 값으로 고정 → 부하가 갑자기 줄 때 인버터 전류 값이 갱신되지 않는 것으로 보임. 인버터 CAN 메시지 주기·지연 확인 필요. 10행 미만 불일치 108번은 두 메시지의 갱신 시점 차이로 보고 결함으로 세지 않음.
- 재현:

```sql
WITH m AS (SELECT row_no, row_no - ROW_NUMBER() OVER (ORDER BY row_no) g FROM sample_clean JOIN session USING (session_id) WHERE label = '오후7차' AND inv_dc_current > 25 AND bms_current <= 0.5) SELECT MIN(row_no) AS 시작_행, COUNT(*) AS 행_수 FROM m GROUP BY g HAVING COUNT(*) >= 10;
```

## DEF-28 [REQ-09] 품질 규칙이 깨진 시각을 모두 잡는다 — 시스템

- 기대: 깨진 시각 3종 탐지율 100%
- 관찰: 99.7%
- 근거: 결함 주입 시험 (faults.py, eval_detection.py)
- 상태: 원인 규명 (2026-11-20): 깨진 시각이 실제 MCU 재시작 바로 앞 행에 오면 '앞뒤 간격 0~200 ms' 조건이 성립하지 않아 놓침 (300개 중 1개). 미조치: 재시작을 먼저 찾고 그 경계를 빼고 비교하는 방법 검토 필요.
- 재현:

```sql
python eval_detection.py
```

## DEF-29 [REQ-11] 품질 규칙이 멀쩡한 행을 깨졌다고 하지 않는다 — 시스템

- 기대: 오탐 0건
- 관찰: 18건
- 근거: 결함 주입 시험
- 상태: 원인 규명 (2026-11-20): 값 검사(규칙 v2)를 넣은 뒤 생김. 18건 모두 심은 결함이나 빠진 샘플에서 2행 안 — 깨진 값과 값이 바뀌는 지점이 붙어 있으면 5행 중앙값이 밀려 바로 옆 정상 행도 표시됨. v1은 오탐 0이었지만 튄 값을 36%만 잡았다(v2는 99.6%). 기준 '0건'을 유지할지(예: 1만 행당 1건 이하로 바꿀지)는 팀 결정 필요.
- 재현:

```sql
python eval_detection.py
```
