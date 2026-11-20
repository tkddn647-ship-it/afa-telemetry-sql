# AI SQL 채점: 설명 v2 · questions.json

**14/17 맞음** · 오류 뒤 다시 짠 질문 1개

| # | 질문 | 결과 | 틀린 이유 |
|--|--|--|--|
| 1 | 세션마다 샘플이 몇 개씩 있어? | 맞음 |  |
| 2 | 차량 속도가 60 km/h를 넘은 샘플은 전부 몇 개야? | 맞음 |  |
| 3 | 세션별 최고 속도와 평균 팩 전압을 알려 줘. | 맞음 | 깨진 값을 빼고 계산 (인정) |
| 4 | 인버터 전류가 25 A를 넘는 샘플이 1,000개 이상인 세션과 그 개수는? | 맞음 |  |
| 5 | 인버터 전류가 25 A를 넘는 구간에서, 보정 계수를 적용한 팩 전류의 세션별 평균은? | 맞음 | 깨진 값을 빼고 계산 (인정) |
| 6 | 전체 평균 속도보다 빠른 샘플이 세션별로 몇 개야? | 맞음 | 값이 0인 세션까지 보여 줌 (인정) |
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
SELECT s.session_id, s.label, COUNT(p.row_no) AS n_samples
FROM session s
LEFT JOIN sample p ON p.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 2. 차량 속도가 60 km/h를 넘은 샘플은 전부 몇 개야?
```sql
SELECT COUNT(*) AS n_samples_over_60kmh
FROM sample_flags
WHERE bad_speed = 0
  AND CAST(vehicle_speed_kmh AS REAL) > 60
```

### 3. 세션별 최고 속도와 평균 팩 전압을 알려 줘.
```sql
SELECT s.session_id,
       s.label,
       MAX(CASE WHEN f.bad_speed = 0 THEN f.vehicle_speed_kmh END) AS max_speed_kmh,
       AVG(CASE WHEN f.bad_bms = 0 THEN f.bms_voltage END) AS avg_pack_voltage_v
FROM session s
LEFT JOIN sample_flags f ON f.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 4. 인버터 전류가 25 A를 넘는 샘플이 1,000개 이상인 세션과 그 개수는?
```sql
SELECT s.session_id,
       s.label,
       COUNT(*) AS n_load_samples
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
       AVG(f.bms_current * (SELECT factor FROM scale_correction WHERE column_name = 'bms_current')) AS avg_bms_current_corr
FROM sample_flags f
JOIN session s ON s.session_id = f.session_id
WHERE f.inv_dc_current > 25
  AND f.bad_inv = 0
  AND f.bad_bms = 0
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 6. 전체 평균 속도보다 빠른 샘플이 세션별로 몇 개야?
```sql
WITH avg_all AS (
  SELECT AVG(vehicle_speed_kmh) AS avg_speed
  FROM sample
  WHERE vehicle_speed_kmh IS NOT NULL
),
cnt AS (
  SELECT s.session_id, COUNT(*) AS n_faster_than_avg
  FROM sample s
  CROSS JOIN avg_all a
  WHERE s.vehicle_speed_kmh > a.avg_speed
  GROUP BY s.session_id
)
SELECT se.session_id,
       se.label,
       COALESCE(c.n_faster_than_avg, 0) AS n_faster_than_avg
FROM session se
LEFT JOIN cnt c ON c.session_id = se.session_id
ORDER BY se.session_id
```

### 7. 인버터 전류가 25 A를 넘는 구간에서 팩 전류를 인버터 전류로 나눈 비율의 세션별 평균은?
```sql
SELECT s.session_id,
       s.label,
       COUNT(*) AS n_rows,
       AVG(f.bms_current * 1.0 / f.inv_dc_current) AS avg_ratio_raw,
       AVG(f.bms_current * sc.factor / f.inv_dc_current) AS avg_ratio_corrected
FROM sample_flags f
JOIN session s ON s.session_id = f.session_id
CROSS JOIN (SELECT factor FROM scale_correction WHERE column_name = 'bms_current') sc
WHERE f.inv_dc_current > 25
  AND f.bad_inv = 0
  AND f.bad_bms = 0
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 8. MCU 시각으로 본 샘플 간격(바로 앞 샘플과의 차이) 중 가장 자주 나온 값 5개와 각각의 횟수는?
```sql
WITH ordered AS (
  SELECT
    session_id,
    row_no,
    stm_ms - LAG(stm_ms) OVER (PARTITION BY session_id ORDER BY row_no) AS d
  FROM sample_flags
  WHERE bad_ms = 0
)
SELECT
  d AS interval_ms,
  COUNT(*) AS cnt
FROM ordered
WHERE d IS NOT NULL
GROUP BY d
ORDER BY cnt DESC, d ASC
LIMIT 5
```

### 9. 인버터 전류가 25 A를 넘는 구간에서 팩 전류/인버터 전류 비율의 세션별 중앙값은?
```sql
WITH load AS (
  SELECT f.session_id,
         f.bms_current * 1.0 / f.inv_dc_current AS ratio
  FROM sample_flags f
  WHERE f.inv_dc_current > 25
    AND COALESCE(f.bad_inv, 0) = 0
    AND COALESCE(f.bad_bms, 0) = 0
    AND f.bms_current IS NOT NULL
),
ranked AS (
  SELECT session_id, ratio,
         ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY ratio) AS rn,
         COUNT(*) OVER (PARTITION BY session_id) AS cnt
  FROM load
)
SELECT r.session_id,
       s.label,
       MAX(r.cnt) AS n_rows,
       AVG(r.ratio) AS median_ratio
FROM ranked r
JOIN session s ON s.session_id = r.session_id
WHERE r.rn IN ((r.cnt + 1) / 2, (r.cnt + 2) / 2)
GROUP BY r.session_id, s.label
ORDER BY r.session_id
```

### 10. 인버터 전류가 25 A를 넘는 상태가 끊기지 않고 이어진 구간은 세션별로 몇 개이고, 가장 긴 구간은 몇 샘플이야?
```sql
WITH load_rows AS (
  SELECT session_id, row_no,
         row_no - ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY row_no) AS grp
  FROM sample_flags
  WHERE inv_dc_current > 25
    AND COALESCE(bad_inv, 0) = 0
    AND COALESCE(bad_bms, 0) = 0
),
segments AS (
  SELECT session_id, grp, COUNT(*) AS seg_len
  FROM load_rows
  GROUP BY session_id, grp
)
SELECT s.session_id,
       s.label,
       COUNT(g.grp) AS segment_count,
       COALESCE(MAX(g.seg_len), 0) AS longest_segment_samples
FROM session s
LEFT JOIN segments g ON g.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 11. 인버터 전류가 25 A를 넘는 구간에서 팩 전류를 인버터 전류에 대해 직선으로 맞추면 세션별 기울기는?
```sql
WITH f AS (
  SELECT factor FROM scale_correction WHERE column_name = 'bms_current'
),
d AS (
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
SELECT d.session_id,
       se.label,
       COUNT(*) AS n_rows,
       (COUNT(*) * SUM(d.x * d.y) - SUM(d.x) * SUM(d.y))
         / (COUNT(*) * SUM(d.x * d.x) - SUM(d.x) * SUM(d.x)) AS slope_corrected
FROM d
JOIN session se ON se.session_id = d.session_id
GROUP BY d.session_id, se.label
HAVING COUNT(*) >= 2
ORDER BY d.session_id
```

### 12. 세션별 샘플 누락률(%)은?
```sql
WITH ok AS (
  SELECT session_id, row_no, CAST(stm_ms AS REAL) AS ms
  FROM sample_flags
  WHERE bad_ms = 0 OR bad_ms IS NULL
),
gaps AS (
  SELECT session_id,
         ms - LAG(ms) OVER (PARTITION BY session_id ORDER BY row_no) AS d
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
       COALESCE(a.received, 0) AS received_samples,
       COALESCE(a.missing, 0) AS missing_samples,
       CASE WHEN COALESCE(a.received, 0) + COALESCE(a.missing, 0) = 0 THEN NULL
            ELSE a.missing * 100.0 / (a.received + a.missing) END AS missing_rate_pct
FROM session s
LEFT JOIN agg a ON a.session_id = s.session_id
ORDER BY s.session_id
```

### 13. 세션별로 깨진 행의 비율(%)은 얼마야?
```sql
SELECT
  s.session_id,
  s.label,
  COUNT(f.row_no) AS total_rows,
  SUM(CASE WHEN f.bad_ms = 1 OR f.bad_inv = 1 OR f.bad_bms = 1 OR f.bad_speed = 1 THEN 1 ELSE 0 END) AS bad_rows,
  SUM(CASE WHEN f.bad_ms = 1 OR f.bad_inv = 1 OR f.bad_bms = 1 OR f.bad_speed = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(f.row_no) AS bad_row_pct
FROM session s
JOIN sample_flags f ON f.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 14. 주행 중에 MCU가 재시작한 횟수를 세션별로 알려 줘.
```sql
WITH good AS (
  SELECT session_id, row_no, CAST(stm_ms AS REAL) AS stm
  FROM sample_flags
  WHERE bad_ms = 0
),
diffs AS (
  SELECT session_id,
         stm - LAG(stm) OVER (PARTITION BY session_id ORDER BY row_no) AS d
  FROM good
)
SELECT s.session_id,
       s.label,
       COALESCE(SUM(CASE WHEN d.d < 0 THEN 1 ELSE 0 END), 0) AS mcu_restart_count
FROM session s
LEFT JOIN diffs d ON d.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 15. 보정 계수를 적용한 뒤에도 인버터 전류가 팩 전류보다 5% 넘게 큰 샘플은 부하 구간에서 세션별로 몇 %야?
```sql
WITH f AS (
  SELECT factor FROM scale_correction WHERE column_name = 'bms_current'
),
load_rows AS (
  SELECT s.session_id, s.inv_dc_current, s.bms_current * f.factor AS bms_current_corr
  FROM sample_flags s CROSS JOIN f
  WHERE s.inv_dc_current > 25
    AND COALESCE(s.bad_inv, 0) = 0
    AND COALESCE(s.bad_bms, 0) = 0
)
SELECT l.session_id,
       se.label,
       COUNT(*) AS load_samples,
       SUM(CASE WHEN l.inv_dc_current > l.bms_current_corr * 1.05 THEN 1 ELSE 0 END) AS over_5pct_samples,
       100.0 * SUM(CASE WHEN l.inv_dc_current > l.bms_current_corr * 1.05 THEN 1 ELSE 0 END) / COUNT(*) AS over_5pct_pct
FROM load_rows l
JOIN session se ON se.session_id = l.session_id
GROUP BY l.session_id, se.label
ORDER BY l.session_id
```

### 16. 세션별로 차를 1초 넘게 멈췄던(기록이 1초 넘게 끊긴) 횟수는?
```sql
WITH good AS (
  SELECT session_id, row_no, stm_ms
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
       COUNT(g.d) AS stop_count
FROM session s
LEFT JOIN gaps g
  ON g.session_id = s.session_id
 AND g.d > 1000
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 17. 오후2차 세션에서 속도가 가장 빨랐던 순간의 속도와 그때 인버터 전류는?
```sql
SELECT s.label,
       f.row_no,
       f.vehicle_speed_kmh,
       f.inv_dc_current
FROM sample_flags f
JOIN session s ON s.session_id = f.session_id
WHERE s.label = '오후2차'
  AND f.bad_speed = 0
  AND f.bad_inv = 0
  AND f.vehicle_speed_kmh IS NOT NULL
ORDER BY f.vehicle_speed_kmh DESC, f.row_no
LIMIT 1
```
