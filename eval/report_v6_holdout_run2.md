# AI SQL 채점: 설명 v6 · holdout.json

**8/8 맞음** · 오류 뒤 다시 짠 질문 0개

| # | 질문 | 결과 | 틀린 이유 |
|--|--|--|--|
| 101 | 세션별로 평균 팩 전압에서 평균 인버터 전압을 빼면 얼마야? | 맞음 |  |
| 102 | 인버터 전류가 25 A를 넘는 구간에서 보정한 팩 전류의 세션별 중앙값은? | 맞음 |  |
| 103 | 세션별로 빠진 샘플은 몇 개야? | 맞음 |  |
| 104 | 속도 값이 튄 행은 세션별로 몇 개야? | 맞음 |  |
| 105 | 세션 전체 샘플 중에 부하 구간 샘플이 차지하는 비율(%)은? | 맞음 |  |
| 106 | 기록이 1초 넘게 끊긴 구간 중 가장 긴 것은 세션별로 몇 초야? | 맞음 |  |
| 107 | 오후6차에서 MCU가 재시작한 순간의 row_no는? | 맞음 |  |
| 108 | 깨진 값은 빼고, 세션별 최대 인버터 전류는? | 맞음 |  |

## AI가 쓴 SQL

### 101. 세션별로 평균 팩 전압에서 평균 인버터 전압을 빼면 얼마야?
```sql
SELECT s.session_id,
       se.label,
       AVG(s.bms_voltage) AS avg_bms_voltage,
       AVG(s.inv_voltage) AS avg_inv_voltage,
       AVG(s.bms_voltage) - AVG(s.inv_voltage) AS diff_v
FROM sample s
JOIN session se ON se.session_id = s.session_id
GROUP BY s.session_id, se.label
ORDER BY s.session_id
```

### 102. 인버터 전류가 25 A를 넘는 구간에서 보정한 팩 전류의 세션별 중앙값은?
```sql
WITH f AS (
  SELECT factor FROM scale_correction WHERE column_name = 'bms_current'
),
load AS (
  SELECT sf.session_id, sf.bms_current * (SELECT factor FROM f) AS cur_corr
  FROM sample_flags sf
  WHERE sf.inv_dc_current > 25
    AND COALESCE(sf.bad_inv, 0) = 0
    AND COALESCE(sf.bad_bms, 0) = 0
    AND sf.bms_current IS NOT NULL
),
ranked AS (
  SELECT session_id, cur_corr,
         ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY cur_corr) AS rn,
         COUNT(*) OVER (PARTITION BY session_id) AS cnt
  FROM load
)
SELECT r.session_id, s.label,
       AVG(r.cur_corr) AS median_bms_current_corr,
       MAX(r.cnt) AS n_rows
FROM ranked r
JOIN session s ON s.session_id = r.session_id
WHERE r.rn IN ((r.cnt + 1) / 2, (r.cnt + 2) / 2)
GROUP BY r.session_id, s.label
ORDER BY r.session_id
```

### 103. 세션별로 빠진 샘플은 몇 개야?
```sql
WITH ok AS (
  SELECT session_id, row_no, CAST(stm_ms AS REAL) AS stm
  FROM sample_flags
  WHERE bad_ms = 0
),
gaps AS (
  SELECT session_id, row_no,
         stm - LAG(stm) OVER (PARTITION BY session_id ORDER BY row_no) AS d,
         row_no - LAG(row_no) OVER (PARTITION BY session_id ORDER BY row_no) - 1 AS n_bad_between
  FROM ok
),
missing AS (
  SELECT session_id,
         SUM(CASE WHEN d > 15 AND d <= 1000
                  THEN MAX(ROUND(d / 10.0) - 1 - n_bad_between, 0)
                  ELSE 0 END) AS missing_samples
  FROM gaps
  GROUP BY session_id
)
SELECT s.session_id,
       s.label,
       COALESCE(m.missing_samples, 0) AS missing_samples
FROM session s
LEFT JOIN missing m ON m.session_id = s.session_id
ORDER BY s.session_id
```

### 104. 속도 값이 튄 행은 세션별로 몇 개야?
```sql
SELECT s.session_id,
       s.label,
       COUNT(DISTINCT vf.row_no) AS spiked_speed_rows
FROM session s
LEFT JOIN value_flag vf
       ON vf.session_id = s.session_id
      AND vf.column_name = 'vehicle_speed_kmh'
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 105. 세션 전체 샘플 중에 부하 구간 샘플이 차지하는 비율(%)은?
```sql
SELECT
  s.session_id,
  s.label,
  COUNT(*) AS total_samples,
  SUM(CASE WHEN f.inv_dc_current > 25
            AND COALESCE(f.bad_inv, 0) = 0
            AND COALESCE(f.bad_bms, 0) = 0
           THEN 1 ELSE 0 END) AS load_samples,
  SUM(CASE WHEN f.inv_dc_current > 25
            AND COALESCE(f.bad_inv, 0) = 0
            AND COALESCE(f.bad_bms, 0) = 0
           THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS load_pct
FROM sample_flags f
JOIN session s ON s.session_id = f.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 106. 기록이 1초 넘게 끊긴 구간 중 가장 긴 것은 세션별로 몇 초야?
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
)
SELECT s.session_id,
       s.label,
       MAX(g.d) / 1000.0 AS longest_gap_sec
FROM session s
JOIN gaps g ON g.session_id = s.session_id
WHERE g.d > 1000
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 107. 오후6차에서 MCU가 재시작한 순간의 row_no는?
```sql
WITH s AS (
  SELECT f.session_id, f.row_no, f.stm_ms
  FROM sample_flags f
  JOIN session se ON se.session_id = f.session_id
  WHERE se.label = '오후6차'
    AND f.bad_ms = 0
),
d AS (
  SELECT session_id, row_no, stm_ms,
         stm_ms - LAG(stm_ms) OVER (PARTITION BY session_id ORDER BY row_no) AS d
  FROM s
)
SELECT se.label, d.row_no, d.d AS gap_ms
FROM d
JOIN session se ON se.session_id = d.session_id
WHERE d.d < 0
ORDER BY d.row_no
```

### 108. 깨진 값은 빼고, 세션별 최대 인버터 전류는?
```sql
SELECT s.session_id,
       s.label,
       MAX(f.inv_dc_current) AS max_inv_dc_current
FROM session s
JOIN sample_flags f
  ON f.session_id = s.session_id
WHERE f.bad_ms = 0
  AND f.bad_inv = 0
  AND f.bad_bms = 0
  AND f.bad_speed = 0
  AND f.bad_value = 0
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```
