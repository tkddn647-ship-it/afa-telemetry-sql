# AI SQL 채점: 설명 v2 · questions.json

**13/17 맞음** · 오류 뒤 다시 짠 질문 0개

| # | 질문 | 결과 | 틀린 이유 |
|--|--|--|--|
| 1 | 세션마다 샘플이 몇 개씩 있어? | 맞음 |  |
| 2 | 차량 속도가 60 km/h를 넘은 샘플은 전부 몇 개야? | 맞음 |  |
| 3 | 세션별 최고 속도와 평균 팩 전압을 알려 줘. | 맞음 | 깨진 값을 빼고 계산 (인정) |
| 4 | 인버터 전류가 25 A를 넘는 샘플이 1,000개 이상인 세션과 그 개수는? | 맞음 |  |
| 5 | 인버터 전류가 25 A를 넘는 구간에서, 보정 계수를 적용한 팩 전류의 세션별 평균은? | 맞음 | 깨진 값을 빼고 계산 (인정) |
| 6 | 전체 평균 속도보다 빠른 샘플이 세션별로 몇 개야? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [5012, 8626, 11822]) |
| 7 | 인버터 전류가 25 A를 넘는 구간에서 팩 전류를 인버터 전류로 나눈 비율의 세션별 평균은? | 맞음 | 깨진 값을 빼고 계산 (인정) |
| 8 | MCU 시각으로 본 샘플 간격(바로 앞 샘플과의 차이) 중 가장 자주 나온 값 5개와 각각의 횟수는? | 맞음 |  |
| 9 | 인버터 전류가 25 A를 넘는 구간에서 팩 전류/인버터 전류 비율의 세션별 중앙값은? | 맞음 |  |
| 10 | 인버터 전류가 25 A를 넘는 상태가 끊기지 않고 이어진 구간은 세션별로 몇 개이고, 가장 긴 구간은 몇 샘플이야? | 맞음 | 값이 0인 세션까지 보여 줌 (인정) |
| 11 | 인버터 전류가 25 A를 넘는 구간에서 팩 전류를 인버터 전류에 대해 직선으로 맞추면 세션별 기울기는? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [0.7456876396865707, 0.7708688370478927, 0.7725126823080775]) |
| 12 | 세션별 샘플 누락률(%)은? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [5.0, 5.0, 5.0]) |
| 13 | 세션별로 깨진 행의 비율(%)은 얼마야? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [0.0, 0.0, 0.0]) |
| 14 | 주행 중에 MCU가 재시작한 횟수를 세션별로 알려 줘. | 맞음 |  |
| 15 | 보정 계수를 적용한 뒤에도 인버터 전류가 팩 전류보다 5% 넘게 큰 샘플은 부하 구간에서 세션별로 몇 %야? | 맞음 |  |
| 16 | 세션별로 차를 1초 넘게 멈췄던(기록이 1초 넘게 끊긴) 횟수는? | 맞음 |  |
| 17 | 오후2차 세션에서 속도가 가장 빨랐던 순간의 속도와 그때 인버터 전류는? | 맞음 |  |

## AI가 쓴 SQL

### 1. 세션마다 샘플이 몇 개씩 있어?
```sql
SELECT s.session_id, s.label, COUNT(sm.row_no) AS n_samples
FROM session s
LEFT JOIN sample sm ON sm.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 2. 차량 속도가 60 km/h를 넘은 샘플은 전부 몇 개야?
```sql
SELECT COUNT(*) AS n_samples_over_60kmh
FROM sample_flags
WHERE vehicle_speed_kmh > 60
  AND bad_speed = 0
```

### 3. 세션별 최고 속도와 평균 팩 전압을 알려 줘.
```sql
SELECT s.session_id,
       s.label,
       MAX(CASE WHEN f.bad_speed = 0 THEN f.vehicle_speed_kmh END) AS max_speed_kmh,
       AVG(CASE WHEN f.bad_bms = 0 THEN f.bms_voltage END) AS avg_bms_voltage_v
FROM session s
LEFT JOIN sample_flags f ON f.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 4. 인버터 전류가 25 A를 넘는 샘플이 1,000개 이상인 세션과 그 개수는?
```sql
SELECT s.session_id, s.label, COUNT(*) AS n_load_samples
FROM sample_flags f
JOIN session s ON s.session_id = f.session_id
WHERE f.inv_dc_current > 25
  AND f.bad_inv = 0
  AND f.bad_bms = 0
GROUP BY s.session_id, s.label
HAVING COUNT(*) >= 1000
ORDER BY n_load_samples DESC
```

### 5. 인버터 전류가 25 A를 넘는 구간에서, 보정 계수를 적용한 팩 전류의 세션별 평균은?
```sql
SELECT s.session_id,
       s.label,
       AVG(f.bms_current * sc.factor) AS avg_pack_current_corr
FROM sample_flags AS f
JOIN session AS s ON s.session_id = f.session_id
CROSS JOIN (SELECT factor FROM scale_correction WHERE column_name = 'bms_current') AS sc
WHERE f.inv_dc_current > 25
  AND COALESCE(f.bad_inv, 0) = 0
  AND COALESCE(f.bad_bms, 0) = 0
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 6. 전체 평균 속도보다 빠른 샘플이 세션별로 몇 개야?
```sql
WITH v AS (
  SELECT session_id, vehicle_speed_kmh
  FROM sample_flags
  WHERE bad_speed = 0 AND vehicle_speed_kmh IS NOT NULL
),
avg_all AS (
  SELECT AVG(vehicle_speed_kmh) AS avg_speed FROM v
)
SELECT s.session_id,
       s.label,
       COUNT(v.vehicle_speed_kmh) AS n_faster_than_avg
FROM session s
LEFT JOIN v
  ON v.session_id = s.session_id
 AND v.vehicle_speed_kmh > (SELECT avg_speed FROM avg_all)
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 7. 인버터 전류가 25 A를 넘는 구간에서 팩 전류를 인버터 전류로 나눈 비율의 세션별 평균은?
```sql
WITH f AS (
  SELECT (SELECT factor FROM scale_correction WHERE column_name = 'bms_current') AS factor
)
SELECT
  s.session_id,
  se.label,
  COUNT(*) AS load_rows,
  AVG(CAST(s.bms_current AS REAL) / CAST(s.inv_dc_current AS REAL)) AS avg_ratio_raw,
  AVG(CAST(s.bms_current AS REAL) * f.factor / CAST(s.inv_dc_current AS REAL)) AS avg_ratio_corrected
FROM sample_flags s
JOIN session se ON se.session_id = s.session_id
CROSS JOIN f
WHERE CAST(s.inv_dc_current AS REAL) > 25
  AND s.bad_inv = 0
  AND s.bad_bms = 0
GROUP BY s.session_id, se.label
ORDER BY s.session_id
```

### 8. MCU 시각으로 본 샘플 간격(바로 앞 샘플과의 차이) 중 가장 자주 나온 값 5개와 각각의 횟수는?
```sql
WITH ordered AS (
  SELECT session_id,
         row_no,
         stm_ms,
         LAG(stm_ms) OVER (PARTITION BY session_id ORDER BY row_no) AS prev_ms
  FROM sample_flags
  WHERE bad_ms = 0 OR bad_ms IS NULL
),
gaps AS (
  SELECT stm_ms - prev_ms AS gap_ms
  FROM ordered
  WHERE prev_ms IS NOT NULL
)
SELECT gap_ms,
       COUNT(*) AS n
FROM gaps
GROUP BY gap_ms
ORDER BY n DESC, gap_ms
LIMIT 5
```

### 9. 인버터 전류가 25 A를 넘는 구간에서 팩 전류/인버터 전류 비율의 세션별 중앙값은?
```sql
WITH fac AS (
  SELECT factor FROM scale_correction WHERE column_name = 'bms_current'
),
f AS (
  SELECT session_id,
         bms_current * 1.0 / inv_dc_current AS r
  FROM sample_flags
  WHERE inv_dc_current > 25
    AND COALESCE(bad_inv, 0) <> 1
    AND COALESCE(bad_bms, 0) <> 1
    AND bms_current IS NOT NULL
),
o AS (
  SELECT session_id, r,
         ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY r) AS rn,
         COUNT(*)     OVER (PARTITION BY session_id)            AS cnt
  FROM f
),
m AS (
  SELECT session_id, AVG(r) AS median_ratio_raw, MAX(cnt) AS n_rows
  FROM o
  WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
  GROUP BY session_id
)
SELECT m.session_id,
       s.label,
       m.n_rows,
       m.median_ratio_raw * (SELECT factor FROM fac) AS median_ratio_corrected,
       m.median_ratio_raw
FROM m
JOIN session s ON s.session_id = m.session_id
ORDER BY m.session_id
```

### 10. 인버터 전류가 25 A를 넘는 상태가 끊기지 않고 이어진 구간은 세션별로 몇 개이고, 가장 긴 구간은 몇 샘플이야?
```sql
WITH load_rows AS (
    SELECT session_id, row_no
    FROM sample_flags
    WHERE inv_dc_current > 25
      AND COALESCE(bad_inv, 0) = 0
      AND COALESCE(bad_bms, 0) = 0
),
grp AS (
    SELECT session_id, row_no,
           row_no - ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY row_no) AS g
    FROM load_rows
),
runs AS (
    SELECT session_id, g, COUNT(*) AS run_len
    FROM grp
    GROUP BY session_id, g
)
SELECT s.session_id,
       s.label,
       COUNT(r.g) AS n_runs,
       COALESCE(MAX(r.run_len), 0) AS longest_run_samples
FROM session s
LEFT JOIN runs r ON r.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 11. 인버터 전류가 25 A를 넘는 구간에서 팩 전류를 인버터 전류에 대해 직선으로 맞추면 세션별 기울기는?
```sql
WITH f AS (
  SELECT factor FROM scale_correction WHERE column_name = 'bms_current'
),
pts AS (
  SELECT s.session_id,
         s.inv_dc_current AS x,
         s.bms_current * (SELECT factor FROM f) AS y
  FROM sample_flags s
  WHERE s.inv_dc_current > 25
    AND s.bad_inv = 0
    AND s.bad_bms = 0
    AND s.inv_dc_current IS NOT NULL
    AND s.bms_current IS NOT NULL
)
SELECT p.session_id,
       se.label,
       COUNT(*) AS n,
       (COUNT(*) * SUM(p.x * p.y) - SUM(p.x) * SUM(p.y)) * 1.0
         / NULLIF(COUNT(*) * SUM(p.x * p.x) - SUM(p.x) * SUM(p.x), 0) AS slope,
       (SUM(p.y) - ((COUNT(*) * SUM(p.x * p.y) - SUM(p.x) * SUM(p.y)) * 1.0
         / NULLIF(COUNT(*) * SUM(p.x * p.x) - SUM(p.x) * SUM(p.x), 0)) * SUM(p.x)) * 1.0
         / COUNT(*) AS intercept
FROM pts p
JOIN session se ON se.session_id = p.session_id
GROUP BY p.session_id, se.label
ORDER BY p.session_id
```

### 12. 세션별 샘플 누락률(%)은?
```sql
WITH ok AS (
  SELECT session_id, row_no, stm_ms
  FROM sample_flags
  WHERE bad_ms = 0
),
gaps AS (
  SELECT session_id,
         stm_ms - LAG(stm_ms) OVER (PARTITION BY session_id ORDER BY row_no) AS d
  FROM ok
),
agg AS (
  SELECT session_id,
         COUNT(*) AS received,
         COALESCE(SUM(CASE WHEN d > 15 AND d <= 1000 THEN ROUND(d / 10.0) - 1 ELSE 0 END), 0) AS missing
  FROM gaps
  GROUP BY session_id
)
SELECT s.session_id,
       s.label,
       a.received,
       a.missing,
       a.missing * 100.0 / (a.received + a.missing) AS missing_rate_pct
FROM session s
JOIN agg a ON a.session_id = s.session_id
ORDER BY s.session_id
```

### 13. 세션별로 깨진 행의 비율(%)은 얼마야?
```sql
SELECT s.session_id,
       s.label,
       COUNT(f.row_no) AS total_rows,
       SUM(CASE WHEN f.bad_ms = 1 OR f.bad_inv = 1 OR f.bad_bms = 1 OR f.bad_speed = 1 THEN 1 ELSE 0 END) AS broken_rows,
       SUM(CASE WHEN f.bad_ms = 1 OR f.bad_inv = 1 OR f.bad_bms = 1 OR f.bad_speed = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(f.row_no) AS broken_pct
FROM session s
JOIN sample_flags f ON f.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 14. 주행 중에 MCU가 재시작한 횟수를 세션별로 알려 줘.
```sql
WITH ordered AS (
  SELECT
    f.session_id,
    f.row_no,
    f.stm_ms - LAG(f.stm_ms) OVER (PARTITION BY f.session_id ORDER BY f.row_no) AS d
  FROM sample_flags f
  WHERE f.bad_ms = 0
)
SELECT
  s.session_id,
  s.label,
  COALESCE(SUM(CASE WHEN o.d < 0 THEN 1 ELSE 0 END), 0) AS mcu_restart_count
FROM session s
LEFT JOIN ordered o
  ON o.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 15. 보정 계수를 적용한 뒤에도 인버터 전류가 팩 전류보다 5% 넘게 큰 샘플은 부하 구간에서 세션별로 몇 %야?
```sql
WITH f AS (
  SELECT factor FROM scale_correction WHERE column_name = 'bms_current'
),
load AS (
  SELECT sf.session_id,
         sf.inv_dc_current,
         sf.bms_current * (SELECT factor FROM f) AS pack_corr
  FROM sample_flags sf
  WHERE sf.inv_dc_current > 25
    AND sf.bad_inv = 0
    AND sf.bad_bms = 0
)
SELECT s.session_id,
       s.label,
       COUNT(*) AS load_samples,
       SUM(CASE WHEN l.inv_dc_current > l.pack_corr * 1.05 THEN 1 ELSE 0 END) AS over_5pct_samples,
       SUM(CASE WHEN l.inv_dc_current > l.pack_corr * 1.05 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS over_5pct_pct
FROM load l
JOIN session s ON s.session_id = l.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 16. 세션별로 차를 1초 넘게 멈췄던(기록이 1초 넘게 끊긴) 횟수는?
```sql
WITH good AS (
  SELECT session_id, row_no, CAST(stm_ms AS INTEGER) AS stm_ms
  FROM sample_flags
  WHERE bad_ms = 0 OR bad_ms IS NULL
),
gaps AS (
  SELECT session_id,
         stm_ms - LAG(stm_ms) OVER (PARTITION BY session_id ORDER BY row_no) AS d
  FROM good
)
SELECT s.session_id,
       s.label,
       COUNT(CASE WHEN g.d > 1000 THEN 1 END) AS stop_count
FROM session s
LEFT JOIN gaps g ON g.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 17. 오후2차 세션에서 속도가 가장 빨랐던 순간의 속도와 그때 인버터 전류는?
```sql
SELECT s.label,
       f.row_no,
       f.vehicle_speed_kmh,
       f.inv_dc_current
FROM sample_flags AS f
JOIN session AS s ON s.session_id = f.session_id
WHERE s.label = '오후2차'
  AND f.bad_speed = 0
  AND f.vehicle_speed_kmh IS NOT NULL
ORDER BY f.vehicle_speed_kmh DESC, f.row_no
LIMIT 1
```
