# AI SQL 채점: 설명 v1 · holdout.json

**3/8 맞음** · 오류 뒤 다시 짠 질문 0개

| # | 질문 | 결과 | 틀린 이유 |
|--|--|--|--|
| 101 | 세션별로 평균 팩 전압에서 평균 인버터 전압을 빼면 얼마야? | 맞음 | 깨진 값을 빼고 계산 (인정) |
| 102 | 인버터 전류가 25 A를 넘는 구간에서 보정한 팩 전류의 세션별 중앙값은? | 맞음 |  |
| 103 | 세션별로 빠진 샘플은 몇 개야? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [118.0, 481.0, 518.0]) |
| 104 | 속도 값이 튄 행은 세션별로 몇 개야? | 맞음 |  |
| 105 | 세션 전체 샘플 중에 부하 구간 샘플이 차지하는 비율(%)은? | 틀림 | 행 수 다름 (정답 10, AI 1) |
| 106 | 기록이 1초 넘게 끊긴 구간 중 가장 긴 것은 세션별로 몇 초야? | 틀림 | 결과 없음 |
| 107 | 오후6차에서 MCU가 재시작한 순간의 row_no는? | 틀림 | 행 수 다름 (정답 2, AI 1) |
| 108 | 깨진 값은 빼고, 세션별 최대 인버터 전류는? | 틀림 | 정답 1번째 열 값과 같은 열이 없음 (정답 예: [0.0, 0.0, 0.0]) |

## AI가 쓴 SQL

### 101. 세션별로 평균 팩 전압에서 평균 인버터 전압을 빼면 얼마야?
```sql
SELECT
  s.session_id,
  s.label,
  AVG(CASE WHEN COALESCE(c.bad_bms, 0) = 0 THEN c.bms_voltage END) AS avg_pack_voltage_v,
  AVG(CASE WHEN COALESCE(c.bad_inv, 0) = 0 THEN c.inv_voltage END) AS avg_inv_voltage_v,
  AVG(CASE WHEN COALESCE(c.bad_bms, 0) = 0 THEN c.bms_voltage END)
    - AVG(CASE WHEN COALESCE(c.bad_inv, 0) = 0 THEN c.inv_voltage END) AS pack_minus_inv_v
FROM session s
LEFT JOIN sample_clean c ON c.session_id = s.session_id
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 102. 인버터 전류가 25 A를 넘는 구간에서 보정한 팩 전류의 세션별 중앙값은?
```sql
WITH f AS (
  SELECT session_id, bms_current_corr AS v
  FROM sample_corrected
  WHERE inv_dc_current > 25
    AND bms_current_corr IS NOT NULL
),
r AS (
  SELECT session_id, v,
         ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY v) AS rn,
         COUNT(*) OVER (PARTITION BY session_id) AS cnt
  FROM f
)
SELECT r.session_id,
       s.label,
       MAX(r.cnt) AS n_rows,
       AVG(r.v) AS median_bms_current_corr
FROM r
JOIN session s ON s.session_id = r.session_id
WHERE r.rn IN ((r.cnt + 1) / 2, (r.cnt + 2) / 2)
GROUP BY r.session_id, s.label
ORDER BY r.session_id
```

### 103. 세션별로 빠진 샘플은 몇 개야?
```sql
SELECT s.session_id,
       s.label,
       s.row_count AS expected_rows,
       COUNT(sm.row_no) AS loaded_rows,
       s.row_count - COUNT(sm.row_no) AS missing_rows
FROM session s
LEFT JOIN sample sm ON sm.session_id = s.session_id
GROUP BY s.session_id, s.label, s.row_count
ORDER BY s.session_id
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
  ROUND(100.0 * SUM(CASE WHEN inv_dc_current > 10 THEN 1 ELSE 0 END) / COUNT(*), 2) AS load_sample_pct
FROM sample
```

### 106. 기록이 1초 넘게 끊긴 구간 중 가장 긴 것은 세션별로 몇 초야?
```sql
WITH ordered AS (
  SELECT
    session_id,
    row_no,
    ts_utc,
    LAG(ts_utc) OVER (PARTITION BY session_id ORDER BY row_no) AS prev_ts
  FROM sample
),
gaps AS (
  SELECT
    session_id,
    (julianday(ts_utc) - julianday(prev_ts)) * 86400.0 AS gap_s
  FROM ordered
  WHERE prev_ts IS NOT NULL AND ts_utc IS NOT NULL
)
SELECT
  s.session_id,
  s.label,
  ROUND(MAX(g.gap_s), 3) AS max_gap_s
FROM gaps g
JOIN session s ON s.session_id = g.session_id
WHERE g.gap_s > 1
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```

### 107. 오후6차에서 MCU가 재시작한 순간의 row_no는?
```sql
WITH s AS (
  SELECT sm.row_no,
         sm.stm_ms,
         LAG(sm.stm_ms, 1)  OVER w AS prev1,
         LAG(sm.stm_ms, 2)  OVER w AS prev2,
         LEAD(sm.stm_ms, 1) OVER w AS next1,
         LEAD(sm.stm_ms, 2) OVER w AS next2
  FROM sample sm
  JOIN session se ON se.session_id = sm.session_id
  WHERE se.label = '오후6차'
    AND sm.stm_ms IS NOT NULL
  WINDOW w AS (ORDER BY sm.row_no)
)
SELECT row_no
FROM s
WHERE stm_ms < prev1
  AND stm_ms < prev2
  AND next1 >= stm_ms
  AND next2 >= next1
ORDER BY (prev1 - stm_ms) DESC
LIMIT 1
```

### 108. 깨진 값은 빼고, 세션별 최대 인버터 전류는?
```sql
SELECT s.session_id,
       s.label,
       MAX(c.inv_dc_current) AS max_inv_dc_current_a
FROM session AS s
LEFT JOIN sample_clean AS c
       ON c.session_id = s.session_id
      AND COALESCE(c.bad_inv, 0) = 0
      AND c.inv_dc_current IS NOT NULL
GROUP BY s.session_id, s.label
ORDER BY s.session_id
```
