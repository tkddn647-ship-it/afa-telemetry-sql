-- 깨진 행: 시각이나 값이 앞뒤와 맞지 않게 튄 행 (01_flags.sql 규칙 v2)
-- 값_튐 = 검사한 30열 중 하나라도 튄 행, 행_손상 = 한 행에서 3열 이상 튄 행 (한 줄 전체가 밀리거나 깨진 것)
SELECT se.label AS 세션, se.row_count AS 전체_행,
       -- 시각_깨짐: MCU 시각이 없는 형식은 NULL
       CASE WHEN se.has_clock THEN SUM(bad_ms) END AS 시각_깨짐, SUM(bad_inv) AS 인버터전류_튐, SUM(bad_bms) AS 팩전류_튐, SUM(bad_speed) AS 속도_튐,
       SUM(bad_value) AS 값_튐, SUM(n_bad_cols >= 3) AS 행_손상,
       SUM(bad_ms OR bad_inv OR bad_bms OR bad_speed OR bad_value) AS 깨진_행,
       ROUND(100.0 * SUM(bad_ms OR bad_inv OR bad_bms OR bad_speed OR bad_value) / se.row_count, 3) AS 깨진_비율_pct
FROM sample_flags JOIN session se USING (session_id)
GROUP BY session_id
ORDER BY session_id;
