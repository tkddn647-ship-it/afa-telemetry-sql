-- 두 전류 신호 사이에 시간 차가 있는지: 팩 전류를 k행(약 10 ms 단위) 앞뒤로 밀어 가며 인버터 전류와의 상관계수를 본다.
-- 상관이 가장 높은 k 가 0이 아니면, 두 신호가 같은 순간을 서로 다른 시각에 기록하고 있다는 뜻이다.
-- (CROSS JOIN은 SQLite가 조인 순서를 바꾸지 않게 하려고 쓴다. 안 쓰면 2분 넘게 걸렸다.)
WITH RECURSIVE ks(k) AS (SELECT -30 UNION ALL SELECT k + 1 FROM ks WHERE k < 30),
load AS MATERIALIZED (
    SELECT session_id, row_no, inv_dc_current AS x FROM sample WHERE inv_dc_current > 25
),
pairs AS (
    SELECT ks.k, a.x, b.bms_current AS y
    FROM load a
    CROSS JOIN ks
    JOIN sample b ON b.session_id = a.session_id AND b.row_no = a.row_no + ks.k
),
agg AS (
    SELECT k, COUNT(*) n, SUM(x) sx, SUM(y) sy, SUM(x*x) sxx, SUM(y*y) syy, SUM(x*y) sxy FROM pairs GROUP BY k
)
SELECT k AS 밀린_행, k * 10 AS 약_ms,
       ROUND((n*sxy - sx*sy) / SQRT((n*sxx - sx*sx) * (n*syy - sy*sy)), 4) AS 상관계수
FROM agg
ORDER BY 상관계수 DESC
LIMIT 5;
