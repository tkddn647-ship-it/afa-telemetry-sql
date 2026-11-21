-- 샘플 누락: MCU는 10 ms마다 보낸다. 깨진 시각 행은 간격 계산에서 빼되, '받은 샘플'로는 센다.
--   5~15 ms   정상
--   15~1000   빠진 샘플 = ROUND(간격/10) - 1 - (그 사이에 있던 깨진 시각 행 수)
--   1000 초과 주행을 멈춘 구간 (누락으로 세지 않음)
--   음수      MCU 재시작 (시계가 0부터 다시 셈)
-- MCU 시각이 없는 형식(session.has_clock = 0, 예: 2026-07 UDP 로거)은 모두 NULL (해당 없음). 0 으로 내면 '누락 없음'으로 읽히므로.
-- (처음 버전은 깨진 시각 행을 빼기만 해서 그 자리를 '빠진 샘플'로 한 번 더 셌다. 결함 주입 시험에서 발견해 고침)
WITH clean AS (
    SELECT session_id, row_no, stm_ms FROM sample_flags WHERE NOT bad_ms
),
gap AS (
    SELECT session_id,
           stm_ms - LAG(stm_ms) OVER w        AS d,
           row_no - LAG(row_no) OVER w - 1    AS skipped
    FROM clean
    WINDOW w AS (PARTITION BY session_id ORDER BY row_no)
),
miss AS (
    SELECT session_id, d,
           CASE WHEN d > 15 AND d <= 1000 THEN MAX(ROUND(d / 10.0) - 1 - skipped, 0) ELSE 0 END AS m
    FROM gap
)
SELECT se.label AS 세션,
       se.row_count AS 받은_샘플,
       CASE WHEN se.has_clock THEN SUM(m) END AS 빠진_샘플,
       CASE WHEN se.has_clock THEN ROUND(100.0 * SUM(m) / (se.row_count + SUM(m)), 1) END AS 누락률_pct,
       CASE WHEN se.has_clock THEN SUM(d > 1000) END AS 멈춘_구간,
       CASE WHEN se.has_clock THEN SUM(d < 0) END    AS MCU_재시작
FROM miss JOIN session se USING (session_id)
GROUP BY session_id
ORDER BY session_id;
