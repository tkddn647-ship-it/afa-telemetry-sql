-- 튄 값 검사 (열 하나). db.refresh_flags 가 value_check 표의 열마다 {col} 을 바꿔 실행하고 결과를 value_flag 에 넣는다.
-- 판정: |값 - 앞뒤 2행씩 5행의 중앙값| > min_dev.  5행이 다 있는 행만 (세션 앞뒤 2행은 판정 안 함).
-- SQLite에는 MEDIAN이 없어서, 5개 값을 한 열로 세운 뒤 정렬해 가운데(3번째)를 고른다.
-- 3행 이상 이어진 값은 5행 안에서 다수가 되어 중앙값이 그 값이 된다 → 1~2행만 나타난 값만 잡힌다.
-- 그 1~2행짜리 값이 실제로 50 ms 이하로만 나타났을 때만 튄 값으로 본다 (CAN 값은 약 100 ms마다 바뀜).
--   샘플이 빠진 곳에서는 정상 프레임도 1~2행만 보일 수 있어서다 (예: 2행이지만 120 ms 동안 유지된 값).
--   지속 시간 = 그 값이 끝난 다음 행의 stm_ms - 그 값이 처음 나온 행의 stm_ms.
--   시각이 깨져 시간을 잴 수 없으면(0 ms 미만 또는 1초 초과) 행 수로만 판단한다.
INSERT INTO value_flag (session_id, row_no, column_name, value, median5)
WITH w AS (
    SELECT session_id, row_no, {col} AS v,
           LAG({col}, 2) OVER o AS a, LAG({col}, 1) OVER o AS b,
           LEAD({col}, 1) OVER o AS d, LEAD({col}, 2) OVER o AS e,
           LAG(stm_ms, 1) OVER o AS tb, stm_ms AS tc, LEAD(stm_ms, 1) OVER o AS td, LEAD(stm_ms, 2) OVER o AS te
    FROM sample
    WHERE session_id IN (SELECT session_id FROM temp.refresh_session)
    WINDOW o AS (PARTITION BY session_id ORDER BY row_no)
), m AS (
    SELECT session_id, row_no, v,
           CASE WHEN v = d THEN te - tc        -- 이 행과 다음 행이 같은 값
                WHEN v = b THEN td - tb        -- 앞 행과 이 행이 같은 값
                ELSE td - tc END AS dur,       -- 이 행만
           (SELECT x FROM (SELECT a AS x UNION ALL SELECT b UNION ALL SELECT v UNION ALL SELECT d UNION ALL SELECT e)
            ORDER BY x LIMIT 1 OFFSET 2) AS med
    FROM w
    WHERE a IS NOT NULL AND b IS NOT NULL AND v IS NOT NULL AND d IS NOT NULL AND e IS NOT NULL
)
SELECT session_id, row_no, '{col}', v, med
FROM m
WHERE ABS(v - med) > (SELECT min_dev FROM value_check WHERE column_name = '{col}')
  AND (dur IS NULL OR dur <= 50 OR dur < 0 OR dur > 1000);
