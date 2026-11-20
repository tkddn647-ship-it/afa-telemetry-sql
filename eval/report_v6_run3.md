# AI SQL 채점: 설명 v6 · questions.json

**16/17 맞음** · 오류 뒤 다시 짠 질문 0개

| # | 질문 | 결과 | 틀린 이유 |
|--|--|--|--|
| 1 | 세션마다 샘플이 몇 개씩 있어? | 맞음 |  |
| 2 | 차량 속도가 60 km/h를 넘은 샘플은 전부 몇 개야? | 맞음 |  |
| 3 | 세션별 최고 속도와 평균 팩 전압을 알려 줘. | 맞음 |  |
| 4 | 인버터 전류가 25 A를 넘는 샘플이 1,000개 이상인 세션과 그 개수는? | 맞음 |  |
| 5 | 인버터 전류가 25 A를 넘는 구간에서, 보정 계수를 적용한 팩 전류의 세션별 평균은? | 맞음 | 깨진 값을 빼고 계산 (인정) |
| 6 | 전체 평균 속도보다 빠른 샘플이 세션별로 몇 개야? | 맞음 | 값이 0인 세션까지 보여 줌 (인정) |
| 7 | 인버터 전류가 25 A를 넘는 구간에서 팩 전류를 인버터 전류로 나눈 비율의 세션별 평균은? | 맞음 | 깨진 값을 빼고 계산 (인정) |
| 8 | MCU 시각으로 본 샘플 간격(바로 앞 샘플과의 차이) 중 가장 자주 나온 값 5개와 각각의 횟수는? | 맞음 |  |
| 9 | 인버터 전류가 25 A를 넘는 구간에서 팩 전류/인버터 전류 비율의 세션별 중앙값은? | 맞음 |  |
| 10 | 인버터 전류가 25 A를 넘는 상태가 끊기지 않고 이어진 구간은 세션별로 몇 개이고, 가장 긴 구간은 몇 샘플이야? | 맞음 | 값이 0인 세션까지 보여 줌 (인정) |
| 11 | 인버터 전류가 25 A를 넘는 구간에서 팩 전류를 인버터 전류에 대해 직선으로 맞추면 세션별 기울기는? | 맞음 |  |
| 12 | 세션별 샘플 누락률(%)은? | 맞음 |  |
| 13 | 세션별로 깨진 행의 비율(%)은 얼마야? | 맞음 |  |
| 14 | 주행 중에 MCU가 재시작한 횟수를 세션별로 알려 줘. | 맞음 |  |
| 15 | 보정 계수를 적용한 뒤에도 인버터 전류가 팩 전류보다 5% 넘게 큰 샘플은 부하 구간에서 세션별로 몇 %야? | 맞음 |  |
| 16 | 세션별로 차를 1초 넘게 멈췄던(기록이 1초 넘게 끊긴) 횟수는? | 맞음 |  |
| 17 | 오후2차 세션에서 속도가 가장 빨랐던 순간의 속도와 그때 인버터 전류는? | 틀림 | 행 수 다름 (정답 1, AI 19) |

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
SELECT COUNT(*) AS n_over_60
FROM sample
WHERE vehicle_speed_kmh > 60
```

### 3. 세션별 최고 속도와 평균 팩 전압을 알려 줘.
```sql
SELECT
  s.session_id,
  se.label,
  MAX(s.vehicle_speed_kmh) AS max_speed_kmh,
  AVG(s.bms_voltage) AS avg_pack_voltage_v
FROM sample AS s
JOIN session AS se ON se.session_id = s.session_id
GROUP BY s.session_id, se.label
ORDER BY s.session_id
```

### 4. 인버터 전류가 25 A를 넘는 샘플이 1,000개 이상인 세션과 그 개수는?
```sql
SELECT f.session_id,
       s.label,
       COUNT(*) AS n_load_samples
FROM sample_flags AS f
JOIN session AS s ON s.session_id = f.session_id
WHERE f.inv_dc_current > 25
  AND f.bad_inv = 0
  AND f.bad_bms = 0
GROUP BY f.session_id, s.label
HAVING COUNT(*) >= 1000
ORDER BY f.session_id
```

### 5. 인버터 전류가 25 A를 넘는 구간에서, 보정 계수를 적용한 팩 전류의 세션별 평균은?
```sql
SELECT s.session_id,
       se.label,
       AVG(s.bms_current * (SELECT factor FROM scale_correction WHERE column_name = 'bms_current')) AS avg_bms_current_corr
FROM sample_flags AS s
JOIN session AS se ON se.session_id = s.session_id
WHERE s.inv_dc_current > 25
  AND s.bad_inv = 0
  AND s.bad_bms = 0
GROUP BY s.session_id, se.label
ORDER BY s.session_id
```

### 6. 전체 평균 속도보다 빠른 샘플이 세션별로 몇 개야?
```sql
WITH avg_speed AS (
  SELECT AVG(vehicle_speed_kmh) AS overall_avg
  FROM sample
)
SELECT
  se.session_id,
  se.label,
  COUNT(s.row_no) AS faster_than_avg_samples
FROM session se
LEFT JOIN sample s
  ON s.session_id = se.session_id
 AND s.vehicle_speed_kmh > (SELECT overall_avg FROM avg_speed)
GROUP BY se.session_id, se.label
ORDER BY se.session_id
```

### 7. 인버터 전류가 25 A를 넘는 구간에서 팩 전류를 인버터 전류로 나눈 비율의 세션별 평균은?
```sql
SELECT s.session_id,
       s.label,
       AVG(f.bms_current * 1.0 / f.inv_dc_current) AS avg_ratio
FROM sample_flags f
JOIN session s ON s.session_id = f.session_id
WHERE f.inv_dc_current > 25
  AND f.bad_inv = 0
  AND f.bad_bms = 0
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 8. MCU 시각으로 본 샘플 간격(바로 앞 샘플과의 차이) 중 가장 자주 나온 값 5개와 각각의 횟수는?
```sql
WITH ok AS (
  SELECT session_id, row_no, CAST(stm_ms AS INTEGER) AS stm
  FROM sample_flags
  WHERE bad_ms = 0 OR bad_ms IS NULL
),
gaps AS (
  SELECT stm - LAG(stm) OVER (PARTITION BY session_id ORDER BY row_no) AS d
  FROM ok
)
SELECT d AS interval_ms, COUNT(*) AS n
FROM gaps
WHERE d IS NOT NULL
GROUP BY d
ORDER BY n DESC, d
LIMIT 5
```

### 9. 인버터 전류가 25 A를 넘는 구간에서 팩 전류/인버터 전류 비율의 세션별 중앙값은?
```sql
WITH load_rows AS (
  SELECT f.session_id,
         CAST(f.bms_current AS REAL) / f.inv_dc_current AS ratio
  FROM sample_flags f
  WHERE f.inv_dc_current > 25
    AND COALESCE(f.bad_inv, 0) = 0
    AND COALESCE(f.bad_bms, 0) = 0
    AND f.bms_current IS NOT NULL
),
ranked AS (
  SELECT session_id,
         ratio,
         ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY ratio) AS rn,
         COUNT(*) OVER (PARTITION BY session_id) AS cnt
  FROM load_rows
)
SELECT r.session_id,
       s.label,
       AVG(r.ratio) AS median_ratio,
       MAX(r.cnt) AS n_rows
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
),
per_session AS (
  SELECT session_id, COUNT(*) AS n_segments, MAX(seg_len) AS longest_segment_samples
  FROM segments
  GROUP BY session_id
)
SELECT s.session_id,
       s.label,
       COALESCE(p.n_segments, 0) AS n_segments,
       COALESCE(p.longest_segment_samples, 0) AS longest_segment_samples
FROM session s
LEFT JOIN per_session p ON p.session_id = s.session_id
ORDER BY s.session_id
```

### 11. 인버터 전류가 25 A를 넘는 구간에서 팩 전류를 인버터 전류에 대해 직선으로 맞추면 세션별 기울기는?
```sql
WITH load_rows AS (
  SELECT f.session_id,
         CAST(f.inv_dc_current AS REAL) AS x,
         CAST(f.bms_current AS REAL) AS y
  FROM sample_flags f
  WHERE f.inv_dc_current > 25
    AND f.bad_inv = 0
    AND f.bad_bms = 0
    AND f.inv_dc_current IS NOT NULL
    AND f.bms_current IS NOT NULL
),
agg AS (
  SELECT session_id,
         COUNT(*) AS n,
         SUM(x) AS sx,
         SUM(y) AS sy,
         SUM(x * x) AS sxx,
         SUM(x * y) AS sxy
  FROM load_rows
  GROUP BY session_id
)
SELECT s.session_id,
       s.label,
       a.n AS n_load_rows,
       (a.n * a.sxy - a.sx * a.sy) * 1.0 / NULLIF(a.n * a.sxx - a.sx * a.sx, 0) AS slope_bms_per_inv,
       (a.sy - ((a.n * a.sxy - a.sx * a.sy) * 1.0 / NULLIF(a.n * a.sxx - a.sx * a.sx, 0)) * a.sx) / a.n AS intercept_a
FROM agg a
JOIN session s ON s.session_id = a.session_id
ORDER BY s.session_id
```

### 12. 세션별 샘플 누락률(%)은?
```sql
WITH g AS (
  SELECT session_id,
         row_no,
         CAST(stm_ms AS REAL) - LAG(CAST(stm_ms AS REAL)) OVER (PARTITION BY session_id ORDER BY row_no) AS d,
         row_no - LAG(row_no) OVER (PARTITION BY session_id ORDER BY row_no) AS dr
  FROM sample_flags
  WHERE bad_ms = 0
),
m AS (
  SELECT session_id,
         SUM(CASE WHEN d > 15 AND d <= 1000
                  THEN MAX(ROUND(d / 10.0) - 1 - (dr - 1), 0)
                  ELSE 0 END) AS missing
  FROM g
  GROUP BY session_id
),
r AS (
  SELECT session_id, COUNT(*) AS received
  FROM sample
  GROUP BY session_id
)
SELECT s.session_id,
       s.label,
       r.received,
       COALESCE(m.missing, 0) AS missing,
       COALESCE(m.missing, 0) * 100.0 / (r.received + COALESCE(m.missing, 0)) AS missing_pct
FROM session s
JOIN r ON r.session_id = s.session_id
LEFT JOIN m ON m.session_id = s.session_id
ORDER BY s.session_id
```

### 13. 세션별로 깨진 행의 비율(%)은 얼마야?
```sql
SELECT s.session_id,
       s.label,
       COUNT(f.row_no) AS total_rows,
       SUM(CASE WHEN f.bad_ms = 1 OR f.bad_inv = 1 OR f.bad_bms = 1 OR f.bad_speed = 1 OR f.bad_value = 1 THEN 1 ELSE 0 END) AS bad_rows,
       SUM(CASE WHEN f.bad_ms = 1 OR f.bad_inv = 1 OR f.bad_bms = 1 OR f.bad_speed = 1 OR f.bad_value = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(f.row_no) AS bad_row_pct
FROM session s
LEFT JOIN sample_flags f ON f.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 14. 주행 중에 MCU가 재시작한 횟수를 세션별로 알려 줘.
```sql
WITH good AS (
  SELECT f.session_id, f.row_no, CAST(f.stm_ms AS REAL) AS ms
  FROM sample_flags f
  WHERE f.bad_ms = 0
),
gaps AS (
  SELECT session_id, row_no,
         ms - LAG(ms) OVER (PARTITION BY session_id ORDER BY row_no) AS d
  FROM good
)
SELECT s.session_id,
       s.label,
       COALESCE(SUM(CASE WHEN g.d < 0 THEN 1 ELSE 0 END), 0) AS mcu_restart_count
FROM session s
LEFT JOIN gaps g ON g.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 15. 보정 계수를 적용한 뒤에도 인버터 전류가 팩 전류보다 5% 넘게 큰 샘플은 부하 구간에서 세션별로 몇 %야?
```sql
WITH f AS (
  SELECT factor FROM scale_correction WHERE column_name = 'bms_current'
),
load AS (
  SELECT sf.session_id, sf.inv_dc_current, sf.bms_current * f.factor AS bms_current_corr
  FROM sample_flags sf CROSS JOIN f
  WHERE sf.inv_dc_current > 25
    AND COALESCE(sf.bad_inv, 0) = 0
    AND COALESCE(sf.bad_bms, 0) = 0
)
SELECT s.session_id,
       s.label,
       COUNT(*) AS load_samples,
       SUM(CASE WHEN l.inv_dc_current > l.bms_current_corr * 1.05 THEN 1 ELSE 0 END) AS over5_samples,
       SUM(CASE WHEN l.inv_dc_current > l.bms_current_corr * 1.05 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS over5_pct
FROM load l
JOIN session s ON s.session_id = l.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
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
       COUNT(CASE WHEN g.d > 1000 THEN 1 END) AS stop_count
FROM session s
LEFT JOIN gaps g ON g.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 17. 오후2차 세션에서 속도가 가장 빨랐던 순간의 속도와 그때 인버터 전류는?
```sql
SELECT se.label,
       s.row_no,
       s.vehicle_speed_kmh,
       s.inv_dc_current
FROM sample AS s
JOIN session AS se ON se.session_id = s.session_id
WHERE se.label = '오후2차'
  AND s.vehicle_speed_kmh = (
        SELECT MAX(s2.vehicle_speed_kmh)
        FROM sample AS s2
        JOIN session AS se2 ON se2.session_id = s2.session_id
        WHERE se2.label = '오후2차'
      )
ORDER BY s.row_no
```
