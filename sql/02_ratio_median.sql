-- [핵심] 부하 구간(인버터 전류 > 25 A)에서 팩 전류 / 인버터 전류 비율의 세션별 중앙값.
-- 인버터는 배터리에서 전류를 받으므로 이 비율은 1 이상이어야 한다. 1보다 작으면 둘 중 하나가 틀렸다.
-- SQLite에는 MEDIAN 함수가 없어서 ROW_NUMBER로 가운데 값을 직접 고른다 (짝수 개면 가운데 두 값의 평균).
WITH load AS (
    SELECT session_id, bms_current / inv_dc_current AS r
    FROM sample
    WHERE inv_dc_current > 25
),
ranked AS (
    SELECT session_id, r,
           ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY r) AS rn,
           COUNT(*)     OVER (PARTITION BY session_id)            AS n
    FROM load
)
SELECT se.label                        AS 세션,
       MAX(n)                          AS 부하_행수,
       ROUND(AVG(r), 3)                AS 비율_중앙값
FROM ranked JOIN session se USING (session_id)
WHERE rn IN ((n + 1) / 2, (n + 2) / 2)
GROUP BY session_id
ORDER BY session_id;
