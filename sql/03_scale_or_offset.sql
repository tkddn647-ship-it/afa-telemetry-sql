-- 배율이 틀린 걸까, 값이 일정하게 더해진(오프셋) 걸까?
-- 부하 구간에서 bms = a * inv + b 로 최소제곱 직선을 맞춘다.
--   배율 오류면 a 는 0.8 근처, b 는 0 근처.  오프셋 오류면 a 는 1 근처, b 가 크게 음수.
WITH load AS (
    SELECT session_id, inv_dc_current AS x, bms_current AS y
    FROM sample_flags
    WHERE inv_dc_current > 25 AND NOT bad_inv AND NOT bad_bms
),
agg AS (
    SELECT session_id, COUNT(*) AS n, SUM(x) sx, SUM(y) sy, SUM(x*x) sxx, SUM(y*y) syy, SUM(x*y) sxy
    FROM load GROUP BY session_id
)
SELECT se.label AS 세션, n AS 행수,
       ROUND((n*sxy - sx*sy) / (n*sxx - sx*sx), 3)                              AS 기울기_a,
       ROUND((sy - (n*sxy - sx*sy) / (n*sxx - sx*sx) * sx) / n, 2)              AS 절편_b_A,
       ROUND(((n*sxy - sx*sy) * (n*sxy - sx*sy)) / ((n*sxx - sx*sx) * (n*syy - sy*sy)), 3) AS 결정계수_R2
FROM agg JOIN session se USING (session_id)
ORDER BY session_id;
