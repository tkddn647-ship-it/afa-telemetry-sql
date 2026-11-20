-- 깨진 행: 시각이나 값이 앞뒤와 맞지 않게 튄 행 (01_flags.sql 규칙)
SELECT se.label AS 세션, se.row_count AS 전체_행,
       SUM(bad_ms) AS 시각_깨짐, SUM(bad_inv) AS 인버터전류_튐, SUM(bad_bms) AS 팩전류_튐, SUM(bad_speed) AS 속도_튐,
       SUM(bad_ms OR bad_inv OR bad_bms OR bad_speed) AS 깨진_행,
       ROUND(100.0 * SUM(bad_ms OR bad_inv OR bad_bms OR bad_speed) / se.row_count, 3) AS 깨진_비율_pct
FROM sample_flags JOIN session se USING (session_id)
GROUP BY session_id
ORDER BY session_id;
