-- 샘플 누락의 구조 (2026-11-21). sql/06 과 같은 간격 계산을 두 갈래로 나눈다.
--   주기 누락: 앞 행과 18~19 ms 떨어진 간격 하나 = 1개 (그 다음 간격은 11 ms). 모든 세션에서 약 200 ms(19~20행)마다 한 번 생기고,
--             ECU 온도 갱신(200 ms 주기)과 시각이 묶여 있다 (온도가 바뀐 행의 87.5%가 직전 19 ms 간격에서 181 ms 뒤).
--             차가 서 있어도 생기므로 통신 문제가 아니라 MCU 루프 일정 문제로 본다 (추정, 정확한 순서는 모름).
--             처음엔 17~21 ms 로 잡았는데, 샘플 하나가 우연히 빠진 20 ms 간격까지 섞여 깨진 행을 지운 사본에서 '주기 누락이 늘었다'는
--             틀린 알림이 났다 (eval_history.py). 실제 주기 간격은 19 ms 가 거의 전부라 18~19 ms 로 좁힘.
--   그 밖 누락: 나머지. 주행 세션에서만 크고, 깨진 행 수와 거의 정비례 (10세션 상관 0.999, 깨진 행이 있는 6세션에서 깨진 행 / 그 밖 누락 = 0.101~0.121,
--             그 밖 누락이 99개뿐인 오후2차를 빼면 0.101~0.109).
--   결합비 = 깨진 행 / 그 밖 누락. 줄이 빠지는 사건과 줄이 깨지는 사건이 같은 원인이면 일정하고,
--           펌웨어 수정(줄 통째로 쓰기 + CRC)이 효과가 있으면 0 에 가까워진다. history.py 가 이 값으로 수정 효과를 판정한다.
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
    SELECT session_id,
           CASE WHEN d > 15 AND d <= 1000 THEN MAX(ROUND(d / 10.0) - 1 - skipped, 0) ELSE 0 END AS m,
           (d BETWEEN 18 AND 19 AND skipped = 0) AS periodic
    FROM gap
),
agg AS (
    SELECT session_id, SUM(m) AS lost, SUM(periodic) AS per FROM miss GROUP BY session_id
),
broken AS (
    SELECT session_id, SUM(bad_ms OR bad_inv OR bad_bms OR bad_speed OR bad_value) AS b FROM sample_flags GROUP BY session_id
)
SELECT se.label AS 세션,
       a.per AS 주기_누락,
       ROUND(100.0 * a.per / (se.row_count + a.lost), 2) AS 주기_누락_pct,
       a.lost - a.per AS 그밖_누락,
       ROUND(100.0 * (a.lost - a.per) / (se.row_count + a.lost), 2) AS 그밖_누락_pct,
       ROUND(1.0 * b.b / NULLIF(a.lost - a.per, 0), 3) AS 결합비
FROM session se JOIN agg a USING (session_id) JOIN broken b USING (session_id)
ORDER BY se.session_id;
