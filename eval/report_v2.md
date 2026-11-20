# AI SQL 채점: 설명 v2 · questions.json

**15/17 맞음** · 오류 뒤 다시 짠 질문 0개

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
| 11 | 인버터 전류가 25 A를 넘는 구간에서 팩 전류를 인버터 전류에 대해 직선으로 맞추면 세션별 기울기는? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [0.7456876396865707, 0.7660127498293625, 0.7703663083221424]) |
| 12 | 세션별 샘플 누락률(%)은? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [5.0, 5.0, 5.0]) |
| 13 | 세션별로 깨진 행의 비율(%)은 얼마야? | 맞음 |  |
| 14 | 주행 중에 MCU가 재시작한 횟수를 세션별로 알려 줘. | 맞음 |  |
| 15 | 보정 계수를 적용한 뒤에도 인버터 전류가 팩 전류보다 5% 넘게 큰 샘플은 부하 구간에서 세션별로 몇 %야? | 맞음 |  |
| 16 | 세션별로 차를 1초 넘게 멈췄던(기록이 1초 넘게 끊긴) 횟수는? | 맞음 |  |
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
SELECT COUNT(*) AS samples_over_60kmh
FROM sample_flags
WHERE bad_speed = 0
  AND vehicle_speed_kmh > 60
```

### 3. 세션별 최고 속도와 평균 팩 전압을 알려 줘.
```sql
SELECT
  s.session_id,
  s.label,
  MAX(CASE WHEN f.bad_speed = 0 THEN f.vehicle_speed_kmh END) AS max_speed_kmh,
  AVG(CASE WHEN f.bad_bms = 0 THEN f.bms_voltage END) AS avg_pack_voltage_v
FROM session AS s
JOIN sample_flags AS f
  ON f.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 4. 인버터 전류가 25 A를 넘는 샘플이 1,000개 이상인 세션과 그 개수는?
```sql
SELECT s.session_id,
       s.label,
       COUNT(*) AS load_samples
FROM sample_flags f
JOIN session s ON s.session_id = f.session_id
WHERE f.inv_dc_current > 25
  AND f.bad_inv = 0
  AND f.bad_bms = 0
GROUP BY s.session_id, s.label
HAVING COUNT(*) >= 1000
ORDER BY load_samples DESC
```

### 5. 인버터 전류가 25 A를 넘는 구간에서, 보정 계수를 적용한 팩 전류의 세션별 평균은?
```sql
SELECT s.session_id,
       s.label,
       AVG(f.bms_current * sc.factor) AS avg_bms_current_corr
FROM sample_flags f
JOIN session s ON s.session_id = f.session_id
CROSS JOIN (SELECT factor FROM scale_correction WHERE column_name = 'bms_current') sc
WHERE f.inv_dc_current > 25
  AND f.bad_inv = 0
  AND f.bad_bms = 0
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 6. 전체 평균 속도보다 빠른 샘플이 세션별로 몇 개야?
```sql
WITH avg_speed AS (
  SELECT AVG(vehicle_speed_kmh) AS v FROM sample
)
SELECT s.session_id,
       s.label,
       COUNT(x.row_no) AS faster_samples
FROM session s
LEFT JOIN sample x
  ON x.session_id = s.session_id
 AND x.vehicle_speed_kmh > (SELECT v FROM avg_speed)
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 7. 인버터 전류가 25 A를 넘는 구간에서 팩 전류를 인버터 전류로 나눈 비율의 세션별 평균은?
```sql
SELECT s.session_id,
       s.label,
       AVG(f.bms_current * 1.0 / f.inv_dc_current) AS avg_pack_to_inv_ratio,
       COUNT(*) AS load_rows
FROM sample_flags f
JOIN session s ON s.session_id = f.session_id
WHERE f.inv_dc_current > 25
  AND COALESCE(f.bad_inv, 0) = 0
  AND COALESCE(f.bad_bms, 0) = 0
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 8. MCU 시각으로 본 샘플 간격(바로 앞 샘플과의 차이) 중 가장 자주 나온 값 5개와 각각의 횟수는?
```sql
WITH f AS (
  SELECT session_id, row_no, CAST(stm_ms AS INTEGER) AS ms
  FROM sample_flags
  WHERE bad_ms = 0 OR bad_ms IS NULL
),
g AS (
  SELECT ms - LAG(ms) OVER (PARTITION BY session_id ORDER BY row_no) AS d
  FROM f
)
SELECT d AS interval_ms, COUNT(*) AS cnt
FROM g
WHERE d IS NOT NULL
GROUP BY d
ORDER BY cnt DESC, d
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
  SELECT session_id,
         ratio,
         ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY ratio) AS rn,
         COUNT(*)     OVER (PARTITION BY session_id)                AS cnt
  FROM load
)
SELECT r.session_id,
       s.label,
       MAX(r.cnt) AS load_rows,
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
runs AS (
  SELECT session_id, grp, COUNT(*) AS run_len
  FROM load_rows
  GROUP BY session_id, grp
)
SELECT s.session_id,
       s.label,
       COUNT(r.grp) AS load_run_count,
       MAX(r.run_len) AS longest_run_samples
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
d AS (
  SELECT s.session_id,
         s.inv_dc_current AS x,
         s.bms_current * (SELECT factor FROM f) AS y
  FROM sample_flags s
  WHERE s.inv_dc_current > 25
    AND COALESCE(s.bad_inv, 0) = 0
    AND COALESCE(s.bad_bms, 0) = 0
    AND s.inv_dc_current IS NOT NULL
    AND s.bms_current IS NOT NULL
),
agg AS (
  SELECT session_id,
         COUNT(*) AS n,
         SUM(x) AS sx,
         SUM(y) AS sy,
         SUM(x * x) AS sxx,
         SUM(x * y) AS sxy
  FROM d
  GROUP BY session_id
)
SELECT a.session_id,
       se.label,
       a.n AS load_rows,
       (a.n * a.sxy - a.sx * a.sy) * 1.0 / NULLIF(a.n * a.sxx - a.sx * a.sx, 0) AS slope,
       (a.sy - ((a.n * a.sxy - a.sx * a.sy) * 1.0 / NULLIF(a.n * a.sxx - a.sx * a.sx, 0)) * a.sx) * 1.0 / a.n AS intercept
FROM agg a
JOIN session se ON se.session_id = a.session_id
ORDER BY a.session_id
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
per AS (
  SELECT session_id,
         COUNT(*) AS received,
         COALESCE(SUM(CASE WHEN d > 15 AND d <= 1000 THEN ROUND(d / 10.0) - 1 ELSE 0 END), 0) AS missing
  FROM gaps
  GROUP BY session_id
)
SELECT s.session_id,
       s.label,
       p.received,
       p.missing,
       p.missing * 100.0 / (p.received + p.missing) AS missing_rate_pct
FROM session s
JOIN per p ON p.session_id = s.session_id
ORDER BY s.session_id
```

### 13. 세션별로 깨진 행의 비율(%)은 얼마야?
```sql
SELECT s.session_id,
       s.label,
       COUNT(f.row_no) AS total_rows,
       SUM(CASE WHEN COALESCE(f.bad_ms,0)=1 OR COALESCE(f.bad_inv,0)=1
                  OR COALESCE(f.bad_bms,0)=1 OR COALESCE(f.bad_speed,0)=1
                THEN 1 ELSE 0 END) AS broken_rows,
       100.0 * SUM(CASE WHEN COALESCE(f.bad_ms,0)=1 OR COALESCE(f.bad_inv,0)=1
                          OR COALESCE(f.bad_bms,0)=1 OR COALESCE(f.bad_speed,0)=1
                        THEN 1 ELSE 0 END) / NULLIF(COUNT(f.row_no),0) AS broken_pct
FROM session s
LEFT JOIN sample_flags f ON f.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 14. 주행 중에 MCU가 재시작한 횟수를 세션별로 알려 줘.
```sql
WITH ordered AS (
  SELECT
    f.session_id,
    f.row_no,
    CAST(f.stm_ms AS REAL) - LAG(CAST(f.stm_ms AS REAL)) OVER (
      PARTITION BY f.session_id ORDER BY f.row_no
    ) AS d
  FROM sample_flags f
  WHERE f.bad_ms = 0 OR f.bad_ms IS NULL
)
SELECT
  s.session_id,
  s.label,
  COALESCE(SUM(CASE WHEN o.d < 0 THEN 1 ELSE 0 END), 0) AS mcu_restart_count
FROM session s
LEFT JOIN ordered o ON o.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 15. 보정 계수를 적용한 뒤에도 인버터 전류가 팩 전류보다 5% 넘게 큰 샘플은 부하 구간에서 세션별로 몇 %야?
```sql
WITH f AS (
  SELECT factor FROM scale_correction WHERE column_name = 'bms_current'
),
load AS (
  SELECT s.session_id,
         s.inv_dc_current,
         s.bms_current * (SELECT factor FROM f) AS bms_current_corr
  FROM sample_flags s
  WHERE s.inv_dc_current > 25
    AND COALESCE(s.bad_inv, 0) = 0
    AND COALESCE(s.bad_bms, 0) = 0
)
SELECT l.session_id,
       se.label,
       COUNT(*) AS load_samples,
       SUM(CASE WHEN l.inv_dc_current > l.bms_current_corr * 1.05 THEN 1 ELSE 0 END) AS inv_gt_pack_5pct,
       SUM(CASE WHEN l.inv_dc_current > l.bms_current_corr * 1.05 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS pct
FROM load l
JOIN session se ON se.session_id = l.session_id
GROUP BY l.session_id, se.label
ORDER BY l.session_id
```

### 16. 세션별로 차를 1초 넘게 멈췄던(기록이 1초 넘게 끊긴) 횟수는?
```sql
WITH ordered AS (
  SELECT session_id,
         row_no,
         CAST(stm_ms AS REAL) - LAG(CAST(stm_ms AS REAL)) OVER (PARTITION BY session_id ORDER BY row_no) AS d
  FROM sample_flags
  WHERE bad_ms = 0 OR bad_ms IS NULL
),
stops AS (
  SELECT session_id, COUNT(*) AS stop_count
  FROM ordered
  WHERE d > 1000
  GROUP BY session_id
)
SELECT s.session_id,
       s.label,
       COALESCE(st.stop_count, 0) AS stop_count
FROM session s
LEFT JOIN stops st ON st.session_id = s.session_id
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
ORDER BY f.vehicle_speed_kmh DESC, f.row_no
LIMIT 1
```
