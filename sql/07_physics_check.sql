-- 물리 기준 확인: 부하 구간에서 인버터 전류가 팩 전류보다 5% 넘게 큰 행의 비율.
-- 보정 전(원본)과, scale_correction 표의 계수를 적용한 뒤를 비교한다.
WITH k AS (SELECT factor FROM scale_correction WHERE column_name = 'bms_current'),
load AS (
    SELECT f.session_id, f.inv_dc_current AS inv, f.bms_current AS bms, f.bms_current * k.factor AS bms_corr
    FROM sample_flags f CROSS JOIN k
    WHERE f.inv_dc_current > 25 AND NOT f.bad_inv AND NOT f.bad_bms
)
SELECT se.label AS 세션,
       COUNT(*) AS 부하_행수,
       ROUND(100.0 * SUM(inv > 1.05 * bms)      / COUNT(*), 1) AS 위반_보정전_pct,
       ROUND(100.0 * SUM(inv > 1.05 * bms_corr) / COUNT(*), 1) AS 위반_보정후_pct
FROM load JOIN session se USING (session_id)
GROUP BY session_id
ORDER BY session_id;
