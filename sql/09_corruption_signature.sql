-- 한 줄 손상의 원인 추정 확인: 계측 코드(afa2026)에서 찾은 두 동작이 로그에 남긴 흔적이 있는지.
--   (1) 라즈베리파이 파서는 칸 수가 모자란 줄의 뒤를 '0'으로 채웠다 → 손상된 줄은 마지막 칸 can2 가 0 이어야 한다
--   (2) MCU 전송 버퍼가 차면 줄 앞부분만 넣고 다음 줄을 버렸다 → 손상된 줄 바로 앞뒤에 샘플 누락이 많아야 한다
-- 행 손상 = 한 행에서 튄 열이 3개 이상 (규칙 v2)
WITH f AS (
    SELECT n_bad_cols, can2,
           (stm_ms - LAG(stm_ms) OVER o > 15) OR (LEAD(stm_ms) OVER o - stm_ms > 15) AS gap_next
    FROM sample_flags
    WINDOW o AS (PARTITION BY session_id ORDER BY row_no)
)
SELECT CASE WHEN n_bad_cols >= 3 THEN '행 손상' WHEN n_bad_cols = 0 THEN '정상 행' ELSE '1~2열만 튐' END AS 행_종류,
       COUNT(*) AS 행_수,
       ROUND(100.0 * AVG(can2 = 0), 3) AS can2_0_pct,
       ROUND(100.0 * AVG(gap_next), 1) AS 바로_옆_누락_pct
FROM f
GROUP BY 1
ORDER BY 2;
