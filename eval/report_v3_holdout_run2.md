# AI SQL 채점: 설명 v3 · holdout.json

**7/8 맞음** · 오류 뒤 다시 짠 질문 2개

| # | 질문 | 결과 | 틀린 이유 |
|--|--|--|--|
| 101 | 세션별로 평균 팩 전압에서 평균 인버터 전압을 빼면 얼마야? | 맞음 |  |
| 102 | 인버터 전류가 25 A를 넘는 구간에서 보정한 팩 전류의 세션별 중앙값은? | 맞음 |  |
| 103 | 세션별로 빠진 샘플은 몇 개야? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [118.0, 481.0, 518.0]) |
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
       AVG(s.bms_voltage) - AVG(s.inv_voltage) AS voltage_diff
FROM sample s
JOIN session se ON se.session_id = s.session_id
GROUP BY s.session_id, se.label
ORDER BY s.session_id
```

### 102. 인버터 전류가 25 A를 넘는 구간에서 보정한 팩 전류의 세션별 중앙값은?
```sql
WITH load AS MATERIALIZED (
  SELECT session_id, bms_current
  FROM sample_flags
  WHERE inv_dc_current > 25
    AND bad_inv = 0
    AND bad_bms = 0
    AND bms_current IS NOT NULL
),
ranked AS MATERIALIZED (
  SELECT session_id, bms_current,
         ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY bms_current) AS rn,
         COUNT(*) OVER (PARTITION BY session_id) AS cnt
  FROM load
),
med AS (
  SELECT session_id, AVG(bms_current) AS median_raw
  FROM ranked
  WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
  GROUP BY session_id
)
SELECT m.session_id,
       s.label,
       m.median_raw * (SELECT factor FROM scale_correction WHERE column_name = 'bms_current') AS median_bms_current_corr
FROM med m
JOIN session s ON s.session_id = m.session_id
ORDER BY m.session_id
```

### 103. 세션별로 빠진 샘플은 몇 개야?
```sql
WITH ok AS MATERIALIZED (
  SELECT session_id, row_no, CAST(stm_ms AS REAL) AS ms
  FROM sample_flags
  WHERE COALESCE(bad_ms, 0) = 0
),
gaps AS MATERIALIZED (
  SELECT session_id,
         ms - LAG(ms) OVER (PARTITION BY session_id ORDER BY row_no) AS d
  FROM ok
),
agg AS MATERIALIZED (
  SELECT session_id,
         SUM(CASE WHEN d > 15 AND d <= 1000 THEN ROUND(d / 10.0) - 1 ELSE 0 END) AS missing_samples
  FROM gaps
  GROUP BY session_id
)
SELECT s.session_id,
       s.label,
       COALESCE(a.missing_samples, 0) AS missing_samples
FROM session s
LEFT JOIN agg a ON a.session_id = s.session_id
ORDER BY s.session_id
```

### 104. 속도 값이 튄 행은 세션별로 몇 개야?
```sql
SELECT s.session_id,
       s.label,
       COALESCE(SUM(CASE WHEN f.bad_speed = 1 THEN 1 ELSE 0 END), 0) AS bad_speed_rows
FROM session s
LEFT JOIN sample_flags f ON f.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 105. 세션 전체 샘플 중에 부하 구간 샘플이 차지하는 비율(%)은?
```sql
SELECT
  s.session_id,
  s.label,
  COUNT(*) AS total_rows,
  SUM(CASE WHEN f.inv_dc_current > 25
            AND COALESCE(f.bad_inv, 0) = 0
            AND COALESCE(f.bad_bms, 0) = 0
           THEN 1 ELSE 0 END) AS load_rows,
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
WITH ordered AS (
  SELECT session_id, row_no,
         stm_ms - LAG(stm_ms) OVER (PARTITION BY session_id ORDER BY row_no) AS d
  FROM sample_flags
  WHERE bad_ms = 0
)
SELECT o.session_id, s.label, MAX(o.d) / 1000.0 AS max_gap_sec
FROM ordered o
JOIN session s ON s.session_id = o.session_id
WHERE o.d > 1000
GROUP BY o.session_id, s.label
ORDER BY o.session_id
```

### 107. 오후6차에서 MCU가 재시작한 순간의 row_no는?
```sql
WITH s AS (
  SELECT f.session_id, f.row_no, CAST(f.stm_ms AS INTEGER) AS stm_ms
  FROM sample_flags f
  JOIN session ss ON ss.session_id = f.session_id
  WHERE ss.label = '오후6차'
    AND f.bad_ms = 0
),
d AS (
  SELECT session_id, row_no,
         stm_ms - LAG(stm_ms) OVER (PARTITION BY session_id ORDER BY row_no) AS d
  FROM s
)
SELECT ss.label, d.row_no
FROM d
JOIN session ss ON ss.session_id = d.session_id
WHERE d.d < 0
ORDER BY d.row_no
```

### 108. 깨진 값은 빼고, 세션별 최대 인버터 전류는?
```sql
SELECT s.session_id,
       s.label,
       MAX(f.inv_dc_current) AS max_inv_dc_current
FROM session s
LEFT JOIN sample_flags f
       ON f.session_id = s.session_id
      AND f.bad_ms = 0
      AND f.bad_inv = 0
      AND f.bad_bms = 0
      AND f.bad_speed = 0
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```
