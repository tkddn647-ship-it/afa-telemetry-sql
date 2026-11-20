# AI SQL 채점: 설명 v4 · holdout.json

**8/8 맞음** · 오류 뒤 다시 짠 질문 0개

| # | 질문 | 결과 | 틀린 이유 |
|--|--|--|--|
| 101 | 세션별로 평균 팩 전압에서 평균 인버터 전압을 빼면 얼마야? | 맞음 |  |
| 102 | 인버터 전류가 25 A를 넘는 구간에서 보정한 팩 전류의 세션별 중앙값은? | 맞음 |  |
| 103 | 세션별로 빠진 샘플은 몇 개야? | 맞음 |  |
| 104 | 속도 값이 튄 행은 세션별로 몇 개야? | 맞음 |  |
| 105 | 세션 전체 샘플 중에 부하 구간 샘플이 차지하는 비율(%)은? | 맞음 |  |
| 106 | 기록이 1초 넘게 끊긴 구간 중 가장 긴 것은 세션별로 몇 초야? | 맞음 | 값이 0인 세션까지 보여 줌 (인정) |
| 107 | 오후6차에서 MCU가 재시작한 순간의 row_no는? | 맞음 |  |
| 108 | 깨진 값은 빼고, 세션별 최대 인버터 전류는? | 맞음 |  |

## AI가 쓴 SQL

### 101. 세션별로 평균 팩 전압에서 평균 인버터 전압을 빼면 얼마야?
```sql
SELECT s.session_id,
       s.label,
       AVG(sa.bms_voltage) AS avg_bms_voltage,
       AVG(sa.inv_voltage) AS avg_inv_voltage,
       AVG(sa.bms_voltage) - AVG(sa.inv_voltage) AS diff_bms_minus_inv_voltage
FROM session s
JOIN sample sa ON sa.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 102. 인버터 전류가 25 A를 넘는 구간에서 보정한 팩 전류의 세션별 중앙값은?
```sql
WITH f AS (
  SELECT factor FROM scale_correction WHERE column_name = 'bms_current'
),
v AS (
  SELECT s.session_id,
         s.bms_current * (SELECT factor FROM f) AS cur
  FROM sample_flags s
  WHERE s.inv_dc_current > 25
    AND s.bad_inv = 0
    AND s.bad_bms = 0
    AND s.bms_current IS NOT NULL
),
r AS (
  SELECT session_id, cur,
         ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY cur) AS rn,
         COUNT(*) OVER (PARTITION BY session_id) AS cnt
  FROM v
)
SELECT r.session_id,
       se.label,
       AVG(r.cur) AS median_bms_current_corr
FROM r
JOIN session se ON se.session_id = r.session_id
WHERE r.rn IN ((r.cnt + 1) / 2, (r.cnt + 2) / 2)
GROUP BY r.session_id, se.label
ORDER BY r.session_id
```

### 103. 세션별로 빠진 샘플은 몇 개야?
```sql
WITH good AS (
  SELECT session_id, row_no, stm_ms,
         LAG(stm_ms) OVER (PARTITION BY session_id ORDER BY row_no) AS prev_ms,
         LAG(row_no) OVER (PARTITION BY session_id ORDER BY row_no) AS prev_row
  FROM sample_flags
  WHERE bad_ms = 0 OR bad_ms IS NULL
),
gaps AS (
  SELECT session_id,
         stm_ms - prev_ms AS d,
         row_no - prev_row - 1 AS n_bad_between
  FROM good
  WHERE prev_ms IS NOT NULL
),
missing AS (
  SELECT session_id,
         SUM(CASE WHEN d > 15 AND d <= 1000
                  THEN MAX(0, ROUND(d / 10.0) - 1 - n_bad_between)
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
       COALESCE(SUM(f.bad_speed = 1), 0) AS bad_speed_rows
FROM session s
LEFT JOIN sample_flags f ON f.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 105. 세션 전체 샘플 중에 부하 구간 샘플이 차지하는 비율(%)은?
```sql
SELECT s.session_id,
       s.label,
       100.0 * SUM(CASE WHEN f.inv_dc_current > 25 AND f.bad_inv = 0 AND f.bad_bms = 0 THEN 1 ELSE 0 END) / COUNT(*) AS load_pct
FROM session s
JOIN sample_flags f ON f.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 106. 기록이 1초 넘게 끊긴 구간 중 가장 긴 것은 세션별로 몇 초야?
```sql
WITH ordered AS (
  SELECT session_id, row_no, stm_ms,
         stm_ms - LAG(stm_ms) OVER (PARTITION BY session_id ORDER BY row_no) AS d
  FROM sample_flags
  WHERE bad_ms = 0
),
stops AS (
  SELECT session_id, MAX(d) / 1000.0 AS longest_stop_sec
  FROM ordered
  WHERE d > 1000
  GROUP BY session_id
)
SELECT s.session_id, s.label, st.longest_stop_sec
FROM session s
LEFT JOIN stops st ON st.session_id = s.session_id
ORDER BY s.session_id
```

### 107. 오후6차에서 MCU가 재시작한 순간의 row_no는?
```sql
WITH s AS (
  SELECT f.session_id, f.row_no, f.stm_ms,
         LAG(f.stm_ms) OVER (PARTITION BY f.session_id ORDER BY f.row_no) AS prev_ms
  FROM sample_flags f
  JOIN session ss ON ss.session_id = f.session_id
  WHERE ss.label = '오후6차' AND f.bad_ms = 0
)
SELECT ss.label, s.row_no, s.prev_ms, s.stm_ms, s.stm_ms - s.prev_ms AS d_ms
FROM s
JOIN session ss ON ss.session_id = s.session_id
WHERE s.prev_ms IS NOT NULL AND s.stm_ms - s.prev_ms < 0
ORDER BY s.row_no
```

### 108. 깨진 값은 빼고, 세션별 최대 인버터 전류는?
```sql
SELECT s.session_id,
       s.label,
       MAX(f.inv_dc_current) AS max_inv_dc_current
FROM session s
LEFT JOIN sample_flags f
  ON f.session_id = s.session_id
 AND COALESCE(f.bad_ms, 0) = 0
 AND COALESCE(f.bad_inv, 0) = 0
 AND COALESCE(f.bad_bms, 0) = 0
 AND COALESCE(f.bad_speed, 0) = 0
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```
