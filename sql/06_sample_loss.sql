-- 샘플 누락: MCU는 10 ms마다 보낸다. 깨진 시각을 뺀 뒤 앞 행과의 간격으로 나눈다.
--   5~15 ms   정상
--   15~1000   빠진 샘플 = ROUND(간격/10) - 1 개
--   1000 초과 주행을 멈춘 구간 (누락으로 세지 않음)
--   음수      MCU 재시작 (시계가 0부터 다시 셈)
WITH clean AS (
    SELECT session_id, row_no, stm_ms FROM sample_flags WHERE NOT bad_ms
),
gap AS (
    SELECT session_id, stm_ms - LAG(stm_ms) OVER (PARTITION BY session_id ORDER BY row_no) AS d
    FROM clean
)
SELECT se.label AS 세션,
       COUNT(d) + 1 AS 받은_샘플,
       SUM(CASE WHEN d > 15 AND d <= 1000 THEN ROUND(d / 10.0) - 1 ELSE 0 END) AS 빠진_샘플,
       ROUND(100.0 * SUM(CASE WHEN d > 15 AND d <= 1000 THEN ROUND(d / 10.0) - 1 ELSE 0 END)
             / (COUNT(d) + 1 + SUM(CASE WHEN d > 15 AND d <= 1000 THEN ROUND(d / 10.0) - 1 ELSE 0 END)), 1) AS 누락률_pct,
       SUM(d > 1000) AS 멈춘_구간,
       SUM(d < 0)    AS MCU_재시작
FROM gap JOIN session se USING (session_id)
GROUP BY session_id
ORDER BY session_id;
