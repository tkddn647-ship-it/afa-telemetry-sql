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
| 15 | 보정 계수를 적용한 뒤에도 인버터 전류가 팩 전류보다 5% 넘게 큰 샘플은 부하 구간에서 세션별로 몇 %야? | 맞음 | 값이 0인 세션까지 보여 줌 (인정) |
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
SELECT s.session_id,
       se.label,
       MAX(s.vehicle_speed_kmh) AS max_speed_kmh,
       AVG(s.bms_voltage) AS avg_pack_voltage_v
FROM sample s
JOIN session se ON se.session_id = s.session_id
GROUP BY s.session_id, se.label
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
ORDER BY s.session_id
```

### 5. 인버터 전류가 25 A를 넘는 구간에서, 보정 계수를 적용한 팩 전류의 세션별 평균은?
```sql
SELECT f.session_id,
       s.label,
       AVG(f.bms_current * (SELECT factor FROM scale_correction WHERE column_name = 'bms_current')) AS avg_bms_current_corr
FROM sample_flags f
JOIN session s ON s.session_id = f.session_id
WHERE f.inv_dc_current > 25
  AND f.bad_inv = 0
  AND f.bad_bms = 0
GROUP BY f.session_id, s.label
ORDER BY f.session_id
```

### 6. 전체 평균 속도보다 빠른 샘플이 세션별로 몇 개야?
```sql
SELECT s.session_id,
       s.label,
       COUNT(sp.row_no) AS faster_samples
FROM session s
LEFT JOIN sample sp
  ON sp.session_id = s.session_id
 AND sp.vehicle_speed_kmh > (SELECT AVG(vehicle_speed_kmh) FROM sample)
GROUP BY s.session_id, s.label
ORDER BY s.session_id
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
WITH ordered AS (
  SELECT s.session_id,
         s.row_no,
         s.stm_ms,
         LAG(s.stm_ms) OVER (PARTITION BY s.session_id ORDER BY s.row_no) AS prev_ms
  FROM sample_flags AS s
  WHERE s.bad_ms = 0 OR s.bad_ms IS NULL
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
WITH load_rows AS (
  SELECT f.session_id,
         f.bms_current * 1.0 / f.inv_dc_current AS ratio
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
       MAX(r.cnt) AS n_load_rows,
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
  SELECT session_id, grp, COUNT(*) AS n_samples
  FROM load_rows
  GROUP BY session_id, grp
)
SELECT s.session_id,
       s.label,
       COUNT(g.grp) AS n_segments,
       COALESCE(MAX(g.n_samples), 0) AS longest_segment_samples
FROM session s
LEFT JOIN segments g ON g.session_id = s.session_id
GROUP BY s.session_id, s.label
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
    AND COALESCE(f.bad_inv, 0) = 0
    AND COALESCE(f.bad_bms, 0) = 0
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
SELECT a.session_id,
       s.label,
       a.n AS n_rows,
       (a.n * a.sxy - a.sx * a.sy) * 1.0 / NULLIF(a.n * a.sxx - a.sx * a.sx, 0) AS slope,
       (a.sy - ((a.n * a.sxy - a.sx * a.sy) * 1.0 / NULLIF(a.n * a.sxx - a.sx * a.sx, 0)) * a.sx) * 1.0 / a.n AS intercept
FROM agg a
JOIN session s ON s.session_id = a.session_id
ORDER BY a.session_id
```

### 12. 세션별 샘플 누락률(%)은?
```sql
WITH good AS (
  SELECT session_id, row_no, CAST(stm_ms AS REAL) AS ms
  FROM sample_flags
  WHERE bad_ms = 0
),
gaps AS (
  SELECT session_id, row_no,
         ms - LAG(ms) OVER (PARTITION BY session_id ORDER BY row_no) AS d,
         row_no - LAG(row_no) OVER (PARTITION BY session_id ORDER BY row_no) - 1 AS n_bad_between
  FROM good
),
miss AS (
  SELECT session_id,
         SUM(CASE WHEN d > 15 AND d <= 1000
                  THEN MAX(ROUND(d / 10.0) - 1 - n_bad_between, 0)
                  ELSE 0 END) AS missing
  FROM gaps
  GROUP BY session_id
),
recv AS (
  SELECT session_id, COUNT(*) AS received
  FROM sample
  GROUP BY session_id
)
SELECT s.session_id,
       s.label,
       r.received,
       COALESCE(m.missing, 0) AS missing,
       COALESCE(m.missing, 0) * 100.0 / (r.received + COALESCE(m.missing, 0)) AS missing_rate_pct
FROM session s
JOIN recv r ON r.session_id = s.session_id
LEFT JOIN miss m ON m.session_id = s.session_id
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
JOIN sample_flags f ON f.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 14. 주행 중에 MCU가 재시작한 횟수를 세션별로 알려 줘.
```sql
WITH ok AS (
  SELECT session_id, row_no, CAST(stm_ms AS REAL) AS stm
  FROM sample_flags
  WHERE bad_ms = 0 OR bad_ms IS NULL
),
d AS (
  SELECT session_id,
         stm - LAG(stm) OVER (PARTITION BY session_id ORDER BY row_no) AS diff
  FROM ok
)
SELECT s.session_id,
       s.label,
       COALESCE(SUM(CASE WHEN d.diff < 0 THEN 1 ELSE 0 END), 0) AS mcu_restarts
FROM session s
LEFT JOIN d ON d.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 15. 보정 계수를 적용한 뒤에도 인버터 전류가 팩 전류보다 5% 넘게 큰 샘플은 부하 구간에서 세션별로 몇 %야?
```sql
WITH f AS (
  SELECT factor FROM scale_correction WHERE column_name = 'bms_current'
),
load_rows AS (
  SELECT sf.session_id, sf.inv_dc_current, sf.bms_current * f.factor AS bms_current_corr
  FROM sample_flags sf CROSS JOIN f
  WHERE sf.inv_dc_current > 25
    AND COALESCE(sf.bad_inv, 0) = 0
    AND COALESCE(sf.bad_bms, 0) = 0
)
SELECT s.session_id,
       s.label,
       COUNT(l.session_id) AS load_samples,
       SUM(CASE WHEN l.inv_dc_current > l.bms_current_corr * 1.05 THEN 1 ELSE 0 END) AS over_5pct_samples,
       100.0 * SUM(CASE WHEN l.inv_dc_current > l.bms_current_corr * 1.05 THEN 1 ELSE 0 END)
             / NULLIF(COUNT(l.session_id), 0) AS over_5pct_pct
FROM session s
LEFT JOIN load_rows l ON l.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 16. 세션별로 차를 1초 넘게 멈췄던(기록이 1초 넘게 끊긴) 횟수는?
```sql
WITH good AS (
  SELECT session_id, row_no, CAST(stm_ms AS REAL) AS ms
  FROM sample_flags
  WHERE bad_ms = 0
),
gaps AS (
  SELECT session_id,
         ms - LAG(ms) OVER (PARTITION BY session_id ORDER BY row_no) AS d
  FROM good
)
SELECT s.session_id,
       s.label,
       COALESCE(SUM(CASE WHEN g.d > 1000 THEN 1 ELSE 0 END), 0) AS stop_count
FROM session s
LEFT JOIN gaps g ON g.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 17. 오후2차 세션에서 속도가 가장 빨랐던 순간의 속도와 그때 인버터 전류는?
```sql
SELECT s.label,
       x.row_no,
       x.vehicle_speed_kmh,
       x.inv_dc_current
FROM sample AS x
JOIN session AS s ON s.session_id = x.session_id
WHERE s.label = '오후2차'
  AND x.vehicle_speed_kmh = (
        SELECT MAX(y.vehicle_speed_kmh)
        FROM sample AS y
        JOIN session AS s2 ON s2.session_id = y.session_id
        WHERE s2.label = '오후2차'
      )
ORDER BY x.row_no
```
