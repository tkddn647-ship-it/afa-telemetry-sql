# AI SQL 채점: 설명 v1 · questions.json

**8/17 맞음** · 오류 뒤 다시 짠 질문 0개

| # | 질문 | 결과 | 틀린 이유 |
|--|--|--|--|
| 1 | 세션마다 샘플이 몇 개씩 있어? | 맞음 |  |
| 2 | 차량 속도가 60 km/h를 넘은 샘플은 전부 몇 개야? | 맞음 | 깨진 값을 빼고 계산 (인정) |
| 3 | 세션별 최고 속도와 평균 팩 전압을 알려 줘. | 맞음 | 깨진 값을 빼고 계산 (인정) |
| 4 | 인버터 전류가 25 A를 넘는 샘플이 1,000개 이상인 세션과 그 개수는? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [4382, 6098, 6352]) |
| 5 | 인버터 전류가 25 A를 넘는 구간에서, 보정 계수를 적용한 팩 전류의 세션별 평균은? | 맞음 |  |
| 6 | 전체 평균 속도보다 빠른 샘플이 세션별로 몇 개야? | 맞음 | 깨진 값을 빼고 계산 (인정) |
| 7 | 인버터 전류가 25 A를 넘는 구간에서 팩 전류를 인버터 전류로 나눈 비율의 세션별 평균은? | 맞음 |  |
| 8 | MCU 시각으로 본 샘플 간격(바로 앞 샘플과의 차이) 중 가장 자주 나온 값 5개와 각각의 횟수는? | 틀림 | 정답 2번째 열 값과 같은 열이 없음 (정답 예: [673, 1139, 10153]) |
| 9 | 인버터 전류가 25 A를 넘는 구간에서 팩 전류/인버터 전류 비율의 세션별 중앙값은? | 맞음 |  |
| 10 | 인버터 전류가 25 A를 넘는 상태가 끊기지 않고 이어진 구간은 세션별로 몇 개이고, 가장 긴 구간은 몇 샘플이야? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [7, 54, 54]) |
| 11 | 인버터 전류가 25 A를 넘는 구간에서 팩 전류를 인버터 전류에 대해 직선으로 맞추면 세션별 기울기는? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [0.7456876396865707, 0.7708688370478927, 0.7725126823080775]) |
| 12 | 세션별 샘플 누락률(%)은? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [5.0, 5.0, 5.0]) |
| 13 | 세션별로 깨진 행의 비율(%)은 얼마야? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [0.0, 0.0, 0.0]) |
| 14 | 주행 중에 MCU가 재시작한 횟수를 세션별로 알려 줘. | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [0, 0, 0]) |
| 15 | 보정 계수를 적용한 뒤에도 인버터 전류가 팩 전류보다 5% 넘게 큰 샘플은 부하 구간에서 세션별로 몇 %야? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [18.3, 21.9, 23.4]) |
| 16 | 세션별로 차를 1초 넘게 멈췄던(기록이 1초 넘게 끊긴) 횟수는? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [0, 0, 0]) |
| 17 | 오후2차 세션에서 속도가 가장 빨랐던 순간의 속도와 그때 인버터 전류는? | 맞음 |  |

## AI가 쓴 SQL

### 1. 세션마다 샘플이 몇 개씩 있어?
```sql
SELECT s.session_id,
       s.label,
       COUNT(m.row_no) AS n_samples
FROM session AS s
LEFT JOIN sample AS m
  ON m.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 2. 차량 속도가 60 km/h를 넘은 샘플은 전부 몇 개야?
```sql
SELECT COUNT(*) AS n_samples_over_60kmh
FROM sample_clean
WHERE vehicle_speed_kmh > 60
  AND COALESCE(bad_speed, 0) = 0
```

### 3. 세션별 최고 속도와 평균 팩 전압을 알려 줘.
```sql
SELECT
  s.session_id,
  s.label,
  MAX(CASE WHEN c.bad_speed = 0 THEN c.vehicle_speed_kmh END) AS max_speed_kmh,
  ROUND(AVG(CASE WHEN c.bad_bms = 0 THEN c.bms_voltage END), 2) AS avg_pack_voltage_v
FROM session AS s
LEFT JOIN sample_clean AS c
  ON c.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 4. 인버터 전류가 25 A를 넘는 샘플이 1,000개 이상인 세션과 그 개수는?
```sql
SELECT s.session_id, se.label, COUNT(*) AS n_samples
FROM sample s
JOIN session se ON se.session_id = s.session_id
WHERE s.inv_dc_current > 25
GROUP BY s.session_id, se.label
HAVING COUNT(*) >= 1000
ORDER BY n_samples DESC
```

### 5. 인버터 전류가 25 A를 넘는 구간에서, 보정 계수를 적용한 팩 전류의 세션별 평균은?
```sql
SELECT s.session_id,
       s.label,
       COUNT(*) AS n_rows,
       AVG(c.bms_current_corr) AS avg_bms_current_corr
FROM sample_corrected AS c
JOIN session AS s ON s.session_id = c.session_id
WHERE c.inv_dc_current > 25
  AND c.bms_current_corr IS NOT NULL
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 6. 전체 평균 속도보다 빠른 샘플이 세션별로 몇 개야?
```sql
WITH clean AS (
  SELECT session_id, vehicle_speed_kmh
  FROM sample_clean
  WHERE vehicle_speed_kmh IS NOT NULL
    AND COALESCE(bad_speed, 0) = 0
),
avg_speed AS (
  SELECT AVG(vehicle_speed_kmh) AS overall_avg FROM clean
)
SELECT s.session_id,
       s.label,
       COUNT(c.vehicle_speed_kmh) AS n_above_avg
FROM session s
LEFT JOIN clean c
  ON c.session_id = s.session_id
 AND c.vehicle_speed_kmh > (SELECT overall_avg FROM avg_speed)
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 7. 인버터 전류가 25 A를 넘는 구간에서 팩 전류를 인버터 전류로 나눈 비율의 세션별 평균은?
```sql
SELECT s.session_id,
       se.label,
       COUNT(*) AS n_rows,
       AVG(s.bms_current * 1.0 / s.inv_dc_current) AS avg_ratio
FROM sample AS s
JOIN session AS se ON se.session_id = s.session_id
WHERE s.inv_dc_current > 25
  AND s.bms_current IS NOT NULL
GROUP BY s.session_id, se.label
ORDER BY s.session_id
```

### 8. MCU 시각으로 본 샘플 간격(바로 앞 샘플과의 차이) 중 가장 자주 나온 값 5개와 각각의 횟수는?
```sql
WITH d AS (
  SELECT stm_ms - LAG(stm_ms) OVER (PARTITION BY session_id ORDER BY row_no) AS dt
  FROM sample
)
SELECT dt AS interval_ms, COUNT(*) AS n
FROM d
WHERE dt IS NOT NULL
GROUP BY dt
ORDER BY n DESC, dt
LIMIT 5
```

### 9. 인버터 전류가 25 A를 넘는 구간에서 팩 전류/인버터 전류 비율의 세션별 중앙값은?
```sql
WITH r AS (
  SELECT session_id,
         CAST(bms_current AS REAL) / inv_dc_current AS ratio
  FROM sample
  WHERE inv_dc_current > 25
    AND bms_current IS NOT NULL
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
       ROUND(AVG(o.ratio), 4) AS median_ratio
FROM o
JOIN session s ON s.session_id = o.session_id
WHERE o.rn IN ((o.cnt + 1) / 2, (o.cnt + 2) / 2)
GROUP BY o.session_id, s.label
ORDER BY o.session_id
```

### 10. 인버터 전류가 25 A를 넘는 상태가 끊기지 않고 이어진 구간은 세션별로 몇 개이고, 가장 긴 구간은 몇 샘플이야?
```sql
WITH ordered AS (
  SELECT session_id, row_no, inv_dc_current,
         ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY row_no) AS rn_all
  FROM sample
),
hot AS (
  SELECT session_id, row_no,
         rn_all - ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY row_no) AS grp
  FROM ordered
  WHERE inv_dc_current > 25
),
runs AS (
  SELECT session_id, grp, COUNT(*) AS run_len
  FROM hot
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
WITH pts AS (
  SELECT s.session_id,
         s.inv_dc_current AS x,
         s.bms_current    AS y
  FROM sample s
  WHERE s.inv_dc_current > 25
    AND s.inv_dc_current IS NOT NULL
    AND s.bms_current IS NOT NULL
),
agg AS (
  SELECT session_id,
         COUNT(*)   AS n,
         SUM(x)     AS sx,
         SUM(y)     AS sy,
         SUM(x * y) AS sxy,
         SUM(x * x) AS sxx
  FROM pts
  GROUP BY session_id
)
SELECT a.session_id,
       se.label,
       a.n,
       ROUND((a.n * a.sxy - a.sx * a.sy) / NULLIF(a.n * a.sxx - a.sx * a.sx, 0), 4) AS slope,
       ROUND((a.sy - ((a.n * a.sxy - a.sx * a.sy) / NULLIF(a.n * a.sxx - a.sx * a.sx, 0)) * a.sx) / a.n, 4) AS intercept
FROM agg a
JOIN session se ON se.session_id = a.session_id
ORDER BY a.session_id
```

### 12. 세션별 샘플 누락률(%)은?
```sql
SELECT s.session_id,
       s.label,
       s.row_count AS expected_rows,
       COUNT(sm.row_no) AS loaded_rows,
       s.row_count - COUNT(sm.row_no) AS missing_rows,
       ROUND(100.0 * (s.row_count - COUNT(sm.row_no)) / NULLIF(s.row_count, 0), 2) AS missing_pct
FROM session s
LEFT JOIN sample sm ON sm.session_id = s.session_id
GROUP BY s.session_id, s.label, s.row_count
ORDER BY s.session_id
```

### 13. 세션별로 깨진 행의 비율(%)은 얼마야?
```sql
SELECT s.session_id,
       s.label,
       COUNT(*) AS total_rows,
       SUM(CASE WHEN c.n_bad_cols > 0 THEN 1 ELSE 0 END) AS bad_rows,
       ROUND(100.0 * SUM(CASE WHEN c.n_bad_cols > 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS bad_pct
FROM sample_clean c
JOIN session s ON s.session_id = c.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 14. 주행 중에 MCU가 재시작한 횟수를 세션별로 알려 줘.
```sql
WITH ms AS (
  SELECT session_id, row_no, stm_ms, vehicle_speed_kmh,
         LAG(stm_ms) OVER (PARTITION BY session_id ORDER BY row_no) AS prev_ms,
         LAG(vehicle_speed_kmh) OVER (PARTITION BY session_id ORDER BY row_no) AS prev_speed
  FROM sample_clean
  WHERE COALESCE(bad_ms, 0) = 0
    AND stm_ms IS NOT NULL
),
restarts AS (
  SELECT session_id, COUNT(*) AS n_restart
  FROM ms
  WHERE prev_ms IS NOT NULL
    AND stm_ms < prev_ms
    AND (COALESCE(vehicle_speed_kmh, 0) > 0 OR COALESCE(prev_speed, 0) > 0)
  GROUP BY session_id
)
SELECT s.session_id, s.label, COALESCE(r.n_restart, 0) AS mcu_restart_while_driving
FROM session s
LEFT JOIN restarts r ON r.session_id = s.session_id
ORDER BY s.session_id
```

### 15. 보정 계수를 적용한 뒤에도 인버터 전류가 팩 전류보다 5% 넘게 큰 샘플은 부하 구간에서 세션별로 몇 %야?
```sql
WITH load AS (
  SELECT c.session_id, c.inv_dc_current, c.bms_current_corr
  FROM sample_corrected c
  WHERE c.inv_dc_current > 10
    AND c.bms_current_corr IS NOT NULL
    AND c.bms_current_corr > 0
)
SELECT s.session_id,
       s.label,
       COUNT(*) AS load_samples,
       SUM(CASE WHEN l.inv_dc_current > 1.05 * l.bms_current_corr THEN 1 ELSE 0 END) AS inv_gt_pack_5pct,
       ROUND(100.0 * SUM(CASE WHEN l.inv_dc_current > 1.05 * l.bms_current_corr THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct
FROM load l
JOIN session s ON s.session_id = l.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 16. 세션별로 차를 1초 넘게 멈췄던(기록이 1초 넘게 끊긴) 횟수는?
```sql
WITH ordered AS (
  SELECT
    session_id,
    row_no,
    (julianday(ts_utc) - julianday(LAG(ts_utc) OVER (PARTITION BY session_id ORDER BY row_no))) * 86400.0 AS gap_s
  FROM sample
)
SELECT
  s.session_id,
  s.label,
  COUNT(o.row_no) AS gap_over_1s_count
FROM session s
LEFT JOIN ordered o
  ON o.session_id = s.session_id
 AND o.gap_s > 1.0
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 17. 오후2차 세션에서 속도가 가장 빨랐던 순간의 속도와 그때 인버터 전류는?
```sql
SELECT c.row_no,
       c.vehicle_speed_kmh AS max_speed_kmh,
       c.inv_dc_current    AS inv_dc_current_a
FROM sample_clean AS c
JOIN session AS s ON s.session_id = c.session_id
WHERE s.label = '오후2차'
  AND c.vehicle_speed_kmh IS NOT NULL
  AND COALESCE(c.bad_speed, 0) = 0
ORDER BY c.vehicle_speed_kmh DESC, c.row_no
LIMIT 1
```
