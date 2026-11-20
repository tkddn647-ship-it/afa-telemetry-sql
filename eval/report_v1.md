# AI SQL 채점: 설명 v1 · questions.json

**9/17 맞음** · 오류 뒤 다시 짠 질문 0개

| # | 질문 | 결과 | 틀린 이유 |
|--|--|--|--|
| 1 | 세션마다 샘플이 몇 개씩 있어? | 맞음 |  |
| 2 | 차량 속도가 60 km/h를 넘은 샘플은 전부 몇 개야? | 맞음 |  |
| 3 | 세션별 최고 속도와 평균 팩 전압을 알려 줘. | 맞음 | 깨진 값을 빼고 계산 (인정) |
| 4 | 인버터 전류가 25 A를 넘는 샘플이 1,000개 이상인 세션과 그 개수는? | 맞음 | 깨진 값을 빼고 계산 (인정) |
| 5 | 인버터 전류가 25 A를 넘는 구간에서, 보정 계수를 적용한 팩 전류의 세션별 평균은? | 맞음 |  |
| 6 | 전체 평균 속도보다 빠른 샘플이 세션별로 몇 개야? | 맞음 | 깨진 값을 빼고 계산 (인정) |
| 7 | 인버터 전류가 25 A를 넘는 구간에서 팩 전류를 인버터 전류로 나눈 비율의 세션별 평균은? | 맞음 | 깨진 값을 빼고 계산 (인정) |
| 8 | MCU 시각으로 본 샘플 간격(바로 앞 샘플과의 차이) 중 가장 자주 나온 값 5개와 각각의 횟수는? | 틀림 | 정답 2번째 열 값과 같은 열이 없음 (정답 예: [673, 1139, 10153]) |
| 9 | 인버터 전류가 25 A를 넘는 구간에서 팩 전류/인버터 전류 비율의 세션별 중앙값은? | 맞음 |  |
| 10 | 인버터 전류가 25 A를 넘는 상태가 끊기지 않고 이어진 구간은 세션별로 몇 개이고, 가장 긴 구간은 몇 샘플이야? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [7, 48, 54]) |
| 11 | 인버터 전류가 25 A를 넘는 구간에서 팩 전류를 인버터 전류에 대해 직선으로 맞추면 세션별 기울기는? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [0.7456876396865707, 0.7660127498293625, 0.7703663083221424]) |
| 12 | 세션별 샘플 누락률(%)은? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [5.0, 5.0, 5.0]) |
| 13 | 세션별로 깨진 행의 비율(%)은 얼마야? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [0.0, 0.0, 0.0]) |
| 14 | 주행 중에 MCU가 재시작한 횟수를 세션별로 알려 줘. | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [0, 0, 0]) |
| 15 | 보정 계수를 적용한 뒤에도 인버터 전류가 팩 전류보다 5% 넘게 큰 샘플은 부하 구간에서 세션별로 몇 %야? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [18.5, 21.9, 23.5]) |
| 16 | 세션별로 차를 1초 넘게 멈췄던(기록이 1초 넘게 끊긴) 횟수는? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [0, 0, 0]) |
| 17 | 오후2차 세션에서 속도가 가장 빨랐던 순간의 속도와 그때 인버터 전류는? | 맞음 |  |

## AI가 쓴 SQL

### 1. 세션마다 샘플이 몇 개씩 있어?
```sql
SELECT s.session_id, s.label, COUNT(sm.row_no) AS sample_count
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
  AND COALESCE(bad_speed, 0) = 0
```

### 3. 세션별 최고 속도와 평균 팩 전압을 알려 줘.
```sql
SELECT
  s.session_id,
  s.label,
  MAX(CASE WHEN c.bad_speed = 0 THEN c.vehicle_speed_kmh END) AS max_speed_kmh,
  AVG(CASE WHEN c.bad_bms = 0 THEN c.bms_voltage END) AS avg_pack_voltage_v
FROM session s
LEFT JOIN sample_clean c ON c.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 4. 인버터 전류가 25 A를 넘는 샘플이 1,000개 이상인 세션과 그 개수는?
```sql
SELECT s.session_id,
       se.label,
       COUNT(*) AS n_samples
FROM sample_clean AS s
JOIN session AS se ON se.session_id = s.session_id
WHERE s.inv_dc_current > 25
GROUP BY s.session_id, se.label
HAVING COUNT(*) >= 1000
ORDER BY n_samples DESC
```

### 5. 인버터 전류가 25 A를 넘는 구간에서, 보정 계수를 적용한 팩 전류의 세션별 평균은?
```sql
SELECT c.session_id,
       s.label,
       COUNT(*) AS n_rows,
       AVG(c.bms_current_corr) AS avg_bms_current_corr
FROM sample_corrected AS c
JOIN session AS s ON s.session_id = c.session_id
WHERE c.inv_dc_current > 25
  AND c.bms_current_corr IS NOT NULL
GROUP BY c.session_id, s.label
ORDER BY c.session_id
```

### 6. 전체 평균 속도보다 빠른 샘플이 세션별로 몇 개야?
```sql
WITH v AS (
  SELECT session_id, vehicle_speed_kmh
  FROM sample_clean
  WHERE vehicle_speed_kmh IS NOT NULL AND COALESCE(bad_speed, 0) = 0
),
avg_speed AS (
  SELECT AVG(vehicle_speed_kmh) AS overall_avg FROM v
)
SELECT s.session_id,
       s.label,
       COUNT(v.vehicle_speed_kmh) AS faster_than_avg_samples
FROM session s
CROSS JOIN avg_speed a
LEFT JOIN v
  ON v.session_id = s.session_id
 AND v.vehicle_speed_kmh > a.overall_avg
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 7. 인버터 전류가 25 A를 넘는 구간에서 팩 전류를 인버터 전류로 나눈 비율의 세션별 평균은?
```sql
SELECT s.session_id,
       s.label,
       COUNT(*) AS n_rows,
       AVG(c.bms_current * 1.0 / c.inv_dc_current) AS avg_ratio
FROM sample_clean AS c
JOIN session AS s ON s.session_id = c.session_id
WHERE c.inv_dc_current > 25
  AND c.bms_current IS NOT NULL
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 8. MCU 시각으로 본 샘플 간격(바로 앞 샘플과의 차이) 중 가장 자주 나온 값 5개와 각각의 횟수는?
```sql
WITH d AS (
  SELECT stm_ms - LAG(stm_ms) OVER (PARTITION BY session_id ORDER BY row_no) AS gap_ms
  FROM sample
)
SELECT gap_ms, COUNT(*) AS cnt
FROM d
WHERE gap_ms IS NOT NULL
GROUP BY gap_ms
ORDER BY cnt DESC, gap_ms
LIMIT 5
```

### 9. 인버터 전류가 25 A를 넘는 구간에서 팩 전류/인버터 전류 비율의 세션별 중앙값은?
```sql
WITH base AS (
  SELECT session_id,
         CAST(bms_current AS REAL) / inv_dc_current AS ratio
  FROM sample_clean
  WHERE inv_dc_current > 25
    AND bms_current IS NOT NULL
),
ranked AS (
  SELECT session_id,
         ratio,
         ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY ratio) AS rn,
         COUNT(*) OVER (PARTITION BY session_id) AS cnt
  FROM base
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
WITH flagged AS (
  SELECT session_id, row_no,
         CASE WHEN inv_dc_current > 25 AND COALESCE(bad_inv, 0) = 0 THEN 1 ELSE 0 END AS hi
  FROM sample_clean
),
grp AS (
  SELECT session_id, row_no, hi,
         ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY row_no)
       - ROW_NUMBER() OVER (PARTITION BY session_id, hi ORDER BY row_no) AS g
  FROM flagged
),
runs AS (
  SELECT session_id, g, COUNT(*) AS run_len
  FROM grp
  WHERE hi = 1
  GROUP BY session_id, g
)
SELECT s.session_id, s.label,
       COUNT(r.g) AS run_count,
       COALESCE(MAX(r.run_len), 0) AS longest_run_samples
FROM session s
LEFT JOIN runs r ON r.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 11. 인버터 전류가 25 A를 넘는 구간에서 팩 전류를 인버터 전류에 대해 직선으로 맞추면 세션별 기울기는?
```sql
WITH pts AS (
  SELECT c.session_id,
         c.inv_dc_current AS x,
         c.bms_current    AS y
  FROM sample_clean c
  WHERE c.inv_dc_current > 25
    AND c.inv_dc_current IS NOT NULL
    AND c.bms_current IS NOT NULL
    AND COALESCE(c.bad_inv, 0) = 0
    AND COALESCE(c.bad_bms, 0) = 0
),
agg AS (
  SELECT session_id,
         COUNT(*)      AS n,
         SUM(x)        AS sx,
         SUM(y)        AS sy,
         SUM(x * x)    AS sxx,
         SUM(x * y)    AS sxy
  FROM pts
  GROUP BY session_id
)
SELECT a.session_id,
       s.label,
       a.n AS n_points,
       ROUND((a.n * a.sxy - a.sx * a.sy) * 1.0 / NULLIF(a.n * a.sxx - a.sx * a.sx, 0), 4) AS slope,
       ROUND((a.sy - ((a.n * a.sxy - a.sx * a.sy) * 1.0 / NULLIF(a.n * a.sxx - a.sx * a.sx, 0)) * a.sx) * 1.0 / a.n, 3) AS intercept
FROM agg a
JOIN session s ON s.session_id = a.session_id
WHERE a.n >= 2
ORDER BY a.session_id
```

### 12. 세션별 샘플 누락률(%)은?
```sql
SELECT
  s.session_id,
  s.label,
  s.row_count AS expected_rows,
  COUNT(DISTINCT sm.row_no) AS loaded_rows,
  s.row_count - COUNT(DISTINCT sm.row_no) AS missing_rows,
  ROUND(100.0 * (s.row_count - COUNT(DISTINCT sm.row_no)) / NULLIF(s.row_count, 0), 2) AS missing_pct
FROM session s
LEFT JOIN sample sm ON sm.session_id = s.session_id
GROUP BY s.session_id, s.label, s.row_count
ORDER BY s.session_id
```

### 13. 세션별로 깨진 행의 비율(%)은 얼마야?
```sql
SELECT
  s.session_id,
  s.label,
  COUNT(*) AS total_rows,
  SUM(CASE WHEN COALESCE(f.bad_ms, 0) <> 0
             OR COALESCE(f.bad_inv, 0) <> 0
             OR COALESCE(f.bad_bms, 0) <> 0
             OR COALESCE(f.bad_speed, 0) <> 0
           THEN 1 ELSE 0 END) AS broken_rows,
  ROUND(100.0 * SUM(CASE WHEN COALESCE(f.bad_ms, 0) <> 0
                           OR COALESCE(f.bad_inv, 0) <> 0
                           OR COALESCE(f.bad_bms, 0) <> 0
                           OR COALESCE(f.bad_speed, 0) <> 0
                         THEN 1 ELSE 0 END) / COUNT(*), 2) AS broken_pct
FROM sample_flags AS f
JOIN session AS s ON s.session_id = f.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 14. 주행 중에 MCU가 재시작한 횟수를 세션별로 알려 줘.
```sql
WITH ordered AS (
  SELECT session_id, row_no, stm_ms, vehicle_speed_kmh,
         LAG(stm_ms) OVER (PARTITION BY session_id ORDER BY row_no) AS prev_ms,
         LAG(vehicle_speed_kmh) OVER (PARTITION BY session_id ORDER BY row_no) AS prev_speed
  FROM sample_clean
  WHERE bad_ms = 0 AND stm_ms IS NOT NULL
),
restarts AS (
  SELECT session_id, COUNT(*) AS restart_count
  FROM ordered
  WHERE prev_ms IS NOT NULL
    AND stm_ms < prev_ms
    AND (COALESCE(prev_speed, 0) > 0 OR COALESCE(vehicle_speed_kmh, 0) > 0)
  GROUP BY session_id
)
SELECT s.session_id, s.label, COALESCE(r.restart_count, 0) AS restart_count
FROM session s
LEFT JOIN restarts r ON r.session_id = s.session_id
ORDER BY s.session_id
```

### 15. 보정 계수를 적용한 뒤에도 인버터 전류가 팩 전류보다 5% 넘게 큰 샘플은 부하 구간에서 세션별로 몇 %야?
```sql
WITH load AS (
  SELECT c.session_id,
         c.inv_dc_current,
         c.bms_current_corr
  FROM sample_corrected AS c
  WHERE c.inv_dc_current > 10
    AND c.bms_current_corr > 0
    AND c.inv_dc_current IS NOT NULL
    AND c.bms_current_corr IS NOT NULL
)
SELECT s.session_id,
       s.label,
       COUNT(*) AS load_samples,
       SUM(CASE WHEN l.inv_dc_current > l.bms_current_corr * 1.05 THEN 1 ELSE 0 END) AS inv_gt_pack_5pct,
       ROUND(100.0 * SUM(CASE WHEN l.inv_dc_current > l.bms_current_corr * 1.05 THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct
FROM load AS l
JOIN session AS s ON s.session_id = l.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 16. 세션별로 차를 1초 넘게 멈췄던(기록이 1초 넘게 끊긴) 횟수는?
```sql
WITH ordered AS (
  SELECT session_id,
         row_no,
         julianday(ts_utc) AS jd,
         LAG(julianday(ts_utc)) OVER (PARTITION BY session_id ORDER BY row_no) AS prev_jd
  FROM sample
),
gaps AS (
  SELECT session_id, COUNT(*) AS gap_count
  FROM ordered
  WHERE prev_jd IS NOT NULL
    AND (jd - prev_jd) * 86400.0 > 1.0
  GROUP BY session_id
)
SELECT s.session_id,
       s.label,
       COALESCE(g.gap_count, 0) AS stop_over_1s_count
FROM session s
LEFT JOIN gaps g ON g.session_id = s.session_id
ORDER BY s.session_id
```

### 17. 오후2차 세션에서 속도가 가장 빨랐던 순간의 속도와 그때 인버터 전류는?
```sql
SELECT c.row_no, c.vehicle_speed_kmh, c.inv_dc_current
FROM sample_clean c
JOIN session s ON s.session_id = c.session_id
WHERE s.label = '오후2차'
  AND c.vehicle_speed_kmh IS NOT NULL
  AND COALESCE(c.bad_speed, 0) = 0
ORDER BY c.vehicle_speed_kmh DESC, c.row_no
LIMIT 1
```
