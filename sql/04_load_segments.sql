-- 부하 구간을 '이어진 덩어리'로 나눠(gaps and islands) 덩어리마다 비율 중앙값을 구한다.
-- 1초(100행) 이상 이어진 덩어리만 본다. 덩어리마다 비율이 거의 같으면 배율 오류라는 판단이 더 단단해진다.
WITH load AS (
    SELECT session_id, row_no, bms_current / inv_dc_current AS r,
           row_no - ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY row_no) AS grp
    FROM sample_flags
    WHERE inv_dc_current > 25 AND NOT bad_inv AND NOT bad_bms
),
seg AS (
    SELECT session_id, grp, r,
           ROW_NUMBER() OVER (PARTITION BY session_id, grp ORDER BY r) AS rn,
           COUNT(*)     OVER (PARTITION BY session_id, grp)            AS n
    FROM load
),
seg_median AS (
    SELECT session_id, grp, MAX(n) AS n, AVG(r) AS med
    FROM seg
    WHERE rn IN ((n + 1) / 2, (n + 2) / 2)
    GROUP BY session_id, grp
    HAVING MAX(n) >= 100
)
SELECT se.label AS 세션, COUNT(*) AS 덩어리_수,
       ROUND(MIN(med), 3) AS 최소_중앙값, ROUND(MAX(med), 3) AS 최대_중앙값
FROM seg_median JOIN session se USING (session_id)
GROUP BY session_id
UNION ALL
SELECT '전체', COUNT(*), ROUND(MIN(med), 3), ROUND(MAX(med), 3) FROM seg_median;
