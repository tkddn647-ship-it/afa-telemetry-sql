# AI SQL 채점: 설명 v5 · questions.json

**16/17 맞음** · 오류 뒤 다시 짠 질문 0개

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
| 11 | 인버터 전류가 25 A를 넘는 구간에서 팩 전류를 인버터 전류에 대해 직선으로 맞추면 세션별 기울기는? | 맞음 |  |
| 12 | 세션별 샘플 누락률(%)은? | 맞음 |  |
| 13 | 세션별로 깨진 행의 비율(%)은 얼마야? | 맞음 |  |
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
FROM sample
WHERE vehicle_speed_kmh > 60
```

### 3. 세션별 최고 속도와 평균 팩 전압을 알려 줘.
```sql
SELECT s.session_id,
       s.label,
       MAX(CASE WHEN f.bad_speed = 0
                 AND NOT EXISTS (SELECT 1 FROM value_flag v
                                 WHERE v.session_id = f.session_id
                                   AND v.row_no = f.row_no
                                   AND v.column_name = 'vehicle_speed_kmh')
                THEN f.vehicle_speed_kmh END) AS max_speed_kmh,
       AVG(CASE WHEN f.bad_bms = 0
                 AND NOT EXISTS (SELECT 1 FROM value_flag v
                                 WHERE v.session_id = f.session_id
                                   AND v.row_no = f.row_no
                                   AND v.column_name = 'bms_voltage')
                THEN f.bms_voltage END) AS avg_bms_voltage_v
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
ORDER BY s.session_id
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
WITH valid AS (
  SELECT session_id, row_no, vehicle_speed_kmh
  FROM sample_flags
  WHERE bad_speed = 0
    AND vehicle_speed_kmh IS NOT NULL
),
overall AS (
  SELECT AVG(vehicle_speed_kmh) AS avg_speed
  FROM valid
)
SELECT
  s.session_id,
  s.label,
  COUNT(v.row_no) AS n_faster_than_avg
FROM session s
LEFT JOIN valid v
  ON v.session_id = s.session_id
 AND v.vehicle_speed_kmh > (SELECT avg_speed FROM overall)
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
WITH ok AS (
  SELECT session_id, row_no, stm_ms
  FROM sample_flags
  WHERE bad_ms = 0
),
gaps AS (
  SELECT session_id, row_no,
         stm_ms - LAG(stm_ms) OVER (PARTITION BY session_id ORDER BY row_no) AS d
  FROM ok
)
SELECT d AS interval_ms, COUNT(*) AS cnt
FROM gaps
WHERE d IS NOT NULL
GROUP BY d
ORDER BY cnt DESC, d
LIMIT 5
```

### 9. 인버터 전류가 25 A를 넘는 구간에서 팩 전류/인버터 전류 비율의 세션별 중앙값은?
```sql
WITH r AS (
  SELECT f.session_id,
         CAST(f.bms_current AS REAL) / f.inv_dc_current AS ratio
  FROM sample_flags f
  WHERE f.inv_dc_current > 25
    AND f.bad_inv = 0
    AND f.bad_bms = 0
    AND f.bms_current IS NOT NULL
),
o AS (
  SELECT session_id, ratio,
         ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY ratio) AS rn,
         COUNT(*) OVER (PARTITION BY session_id) AS cnt
  FROM r
)
SELECT o.session_id,
       s.label,
       MAX(o.cnt) AS n_rows,
       AVG(o.ratio) AS median_ratio
FROM o
JOIN session s ON s.session_id = o.session_id
WHERE o.rn IN ((o.cnt + 1) / 2, (o.cnt + 2) / 2)
GROUP BY o.session_id, s.label
ORDER BY o.session_id
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
runs AS (
  SELECT session_id, grp, COUNT(*) AS run_len
  FROM load_rows
  GROUP BY session_id, grp
)
SELECT s.session_id,
       s.label,
       COUNT(r.grp) AS n_runs,
       COALESCE(MAX(r.run_len), 0) AS longest_run_samples
FROM session s
LEFT JOIN runs r ON r.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 11. 인버터 전류가 25 A를 넘는 구간에서 팩 전류를 인버터 전류에 대해 직선으로 맞추면 세션별 기울기는?
```sql
WITH load AS (
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
  FROM load
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
  SELECT session_id, row_no, stm_ms,
         LAG(stm_ms) OVER (PARTITION BY session_id ORDER BY row_no) AS prev_ms,
         LAG(row_no) OVER (PARTITION BY session_id ORDER BY row_no) AS prev_row
  FROM sample_flags
  WHERE bad_ms = 0
),
gaps AS (
  SELECT session_id,
         SUM(CASE WHEN prev_ms IS NOT NULL
                   AND (stm_ms - prev_ms) > 15 AND (stm_ms - prev_ms) <= 1000
                  THEN MAX(0, ROUND((stm_ms - prev_ms) / 10.0) - 1 - (row_no - prev_row - 1))
                  ELSE 0 END) AS missing
  FROM good
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
       COALESCE(g.missing, 0) AS missing,
       COALESCE(g.missing, 0) * 100.0 / (r.received + COALESCE(g.missing, 0)) AS missing_rate_pct
FROM session s
JOIN recv r ON r.session_id = s.session_id
LEFT JOIN gaps g ON g.session_id = s.session_id
ORDER BY s.session_id
```

### 13. 세션별로 깨진 행의 비율(%)은 얼마야?
```sql
SELECT s.session_id,
       s.label,
       COUNT(f.row_no) AS total_rows,
       COALESCE(SUM(CASE WHEN f.bad_ms = 1 OR f.bad_inv = 1 OR f.bad_bms = 1 OR f.bad_speed = 1 OR f.bad_value = 1 THEN 1 ELSE 0 END), 0) AS bad_rows,
       COALESCE(SUM(CASE WHEN f.bad_ms = 1 OR f.bad_inv = 1 OR f.bad_bms = 1 OR f.bad_speed = 1 OR f.bad_value = 1 THEN 1 ELSE 0 END), 0) * 100.0
         / NULLIF(COUNT(f.row_no), 0) AS bad_row_pct
FROM session s
LEFT JOIN sample_flags f ON f.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 14. 주행 중에 MCU가 재시작한 횟수를 세션별로 알려 줘.
```sql
WITH good AS (
  SELECT session_id, row_no, CAST(stm_ms AS REAL) AS ms
  FROM sample_flags
  WHERE bad_ms = 0
),
diffs AS (
  SELECT session_id, row_no,
         ms - LAG(ms) OVER (PARTITION BY session_id ORDER BY row_no) AS d
  FROM good
)
SELECT s.session_id,
       s.label,
       COALESCE(SUM(CASE WHEN d.d < 0 THEN 1 ELSE 0 END), 0) AS mcu_restarts
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
load AS (
  SELECT sf.session_id,
         sf.inv_dc_current,
         sf.bms_current * (SELECT factor FROM f) AS bms_current_corr
  FROM sample_flags sf
  WHERE sf.inv_dc_current > 25
    AND sf.bad_inv = 0
    AND sf.bad_bms = 0
)
SELECT s.session_id,
       s.label,
       COUNT(*) AS load_samples,
       SUM(CASE WHEN l.inv_dc_current > l.bms_current_corr * 1.05 THEN 1 ELSE 0 END) AS over_5pct_samples,
       SUM(CASE WHEN l.inv_dc_current > l.bms_current_corr * 1.05 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS over_5pct_pct
FROM load l
JOIN session s ON s.session_id = l.session_id
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
       f.row_no,
       f.vehicle_speed_kmh AS max_speed_kmh,
       f.inv_dc_current
FROM sample_flags f
JOIN session s ON s.session_id = f.session_id
WHERE s.label = '오후2차'
  AND f.vehicle_speed_kmh IS NOT NULL
  AND COALESCE(f.bad_ms, 0) = 0
  AND COALESCE(f.bad_inv, 0) = 0
  AND COALESCE(f.bad_bms, 0) = 0
  AND COALESCE(f.bad_speed, 0) = 0
  AND COALESCE(f.bad_value, 0) = 0
ORDER BY f.vehicle_speed_kmh DESC, f.row_no
LIMIT 1
```
