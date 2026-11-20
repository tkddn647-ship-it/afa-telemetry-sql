# AI SQL 채점: 설명 v1 · holdout.json

**4/8 맞음** · 오류 뒤 다시 짠 질문 0개

| # | 질문 | 결과 | 틀린 이유 |
|--|--|--|--|
| 101 | 세션별로 평균 팩 전압에서 평균 인버터 전압을 빼면 얼마야? | 맞음 | 깨진 값을 빼고 계산 (인정) |
| 102 | 인버터 전류가 25 A를 넘는 구간에서 보정한 팩 전류의 세션별 중앙값은? | 맞음 |  |
| 103 | 세션별로 빠진 샘플은 몇 개야? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [118.0, 481.0, 518.0]) |
| 104 | 속도 값이 튄 행은 세션별로 몇 개야? | 맞음 |  |
| 105 | 세션 전체 샘플 중에 부하 구간 샘플이 차지하는 비율(%)은? | 틀림 | 행 수 다름 (정답 10, AI 1) |
| 106 | 기록이 1초 넘게 끊긴 구간 중 가장 긴 것은 세션별로 몇 초야? | 틀림 | 결과 없음 |
| 107 | 오후6차에서 MCU가 재시작한 순간의 row_no는? | 틀림 | 행 수 다름 (정답 2, AI 1) |
| 108 | 깨진 값은 빼고, 세션별 최대 인버터 전류는? | 맞음 |  |

## AI가 쓴 SQL

### 101. 세션별로 평균 팩 전압에서 평균 인버터 전압을 빼면 얼마야?
```sql
SELECT s.session_id,
       s.label,
       AVG(c.bms_voltage) AS avg_pack_voltage,
       AVG(c.inv_voltage) AS avg_inv_voltage,
       AVG(c.bms_voltage) - AVG(c.inv_voltage) AS diff_v
FROM session s
JOIN sample_clean c ON c.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 102. 인버터 전류가 25 A를 넘는 구간에서 보정한 팩 전류의 세션별 중앙값은?
```sql
WITH t AS (
  SELECT session_id,
         bms_current_corr AS v,
         ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY bms_current_corr) AS rn,
         COUNT(*) OVER (PARTITION BY session_id) AS cnt
  FROM sample_corrected
  WHERE inv_dc_current > 25
    AND bms_current_corr IS NOT NULL
)
SELECT t.session_id,
       s.label,
       MAX(t.cnt) AS n_rows,
       AVG(t.v) AS median_bms_current_corr
FROM t
JOIN session s ON s.session_id = t.session_id
WHERE t.rn IN ((t.cnt + 1) / 2, (t.cnt + 2) / 2)
GROUP BY t.session_id, s.label
ORDER BY t.session_id
```

### 103. 세션별로 빠진 샘플은 몇 개야?
```sql
WITH s AS (
  SELECT session_id,
         COUNT(*)              AS loaded_rows,
         MIN(row_no)           AS min_row,
         MAX(row_no)           AS max_row
  FROM sample
  GROUP BY session_id
)
SELECT se.session_id,
       se.label,
       se.row_count                                   AS expected_rows,
       COALESCE(s.loaded_rows, 0)                     AS loaded_rows,
       se.row_count - COALESCE(s.loaded_rows, 0)      AS missing_vs_row_count,
       COALESCE(s.max_row - s.min_row + 1 - s.loaded_rows, 0) AS missing_row_no_gaps
FROM session se
LEFT JOIN s ON s.session_id = se.session_id
ORDER BY se.session_id
```

### 104. 속도 값이 튄 행은 세션별로 몇 개야?
```sql
SELECT s.session_id,
       s.label,
       COUNT(f.row_no) AS bad_speed_rows
FROM session AS s
LEFT JOIN sample_flags AS f
  ON f.session_id = s.session_id
 AND f.bad_speed = 1
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 105. 세션 전체 샘플 중에 부하 구간 샘플이 차지하는 비율(%)은?
```sql
SELECT
  ROUND(100.0 * SUM(CASE WHEN inv_dc_current > 10 THEN 1 ELSE 0 END) / COUNT(*), 2) AS load_ratio_pct
FROM sample
```

### 106. 기록이 1초 넘게 끊긴 구간 중 가장 긴 것은 세션별로 몇 초야?
```sql
WITH ordered AS (
  SELECT
    session_id,
    row_no,
    (julianday(ts_utc) - julianday(LAG(ts_utc) OVER (PARTITION BY session_id ORDER BY row_no))) * 86400.0 AS gap_s
  FROM sample
  WHERE ts_utc IS NOT NULL
)
SELECT
  o.session_id,
  s.label,
  ROUND(MAX(o.gap_s), 3) AS max_gap_s,
  COUNT(*) AS n_gaps_over_1s
FROM ordered o
JOIN session s ON s.session_id = o.session_id
WHERE o.gap_s > 1.0
GROUP BY o.session_id, s.label
ORDER BY o.session_id
```

### 107. 오후6차에서 MCU가 재시작한 순간의 row_no는?
```sql
WITH s AS (
  SELECT row_no, stm_ms,
         LAG(stm_ms, 1) OVER (ORDER BY row_no) AS prev1,
         LAG(stm_ms, 2) OVER (ORDER BY row_no) AS prev2,
         LEAD(stm_ms, 1) OVER (ORDER BY row_no) AS next1,
         LEAD(stm_ms, 2) OVER (ORDER BY row_no) AS next2
  FROM sample
  WHERE session_id = (SELECT session_id FROM session WHERE label = '오후6차')
    AND stm_ms IS NOT NULL
)
SELECT row_no
FROM s
WHERE stm_ms < prev1 - 1000
  AND stm_ms < prev2 - 1000
  AND next1 >= stm_ms AND next1 < prev1
  AND next2 >= next1 AND next2 < prev1
ORDER BY (prev1 - stm_ms) DESC
LIMIT 1
```

### 108. 깨진 값은 빼고, 세션별 최대 인버터 전류는?
```sql
SELECT s.session_id,
       se.label,
       MAX(s.inv_dc_current) AS max_inv_dc_current_a
FROM sample_clean AS s
JOIN session AS se ON se.session_id = s.session_id
WHERE s.bad_inv = 0
  AND s.inv_dc_current IS NOT NULL
  AND NOT EXISTS (
        SELECT 1
        FROM value_flag AS vf
        WHERE vf.session_id = s.session_id
          AND vf.row_no = s.row_no
          AND vf.column_name = 'inv_dc_current'
      )
GROUP BY s.session_id, se.label
ORDER BY s.session_id
```
