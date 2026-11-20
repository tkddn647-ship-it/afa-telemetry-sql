-- 여러 신호를 함께 보는 검사 (깨진 행을 뺀 sample_clean 기준). 세션마다 한 줄.
--   [프리차지] 메인 접촉기 신호가 0 -> 1 이 되는 순간 인버터(차량 쪽) 전압이 팩 전압의 90% 이상이어야 한다
--              (KSAE 대학생 자작자동차대회 차량기술규정 제52조 ①. FS Rules 2026 EV5.7.1 은 95%)
--              주의: 지금 펌웨어는 motor_main_contactor 를 인버터 VSM 상태 >= 2 ('Pre-charge Active')로 만든다 (can_vehicle.c).
--              그래서 이 로그의 0 -> 1 은 접촉기 닫힘이 아니라 초기충전 시작이고, 이 판정은 펌웨어를 고치기 전엔 뜻이 없다.
--   [전류 일치] 인버터 전류 > 25 A 인데 팩 전류 <= 0.5 A 인 상태가 10행(CAN 한 주기, 약 100 ms) 이상 이어지면 불일치 1번
--              10행 미만은 두 CAN 메시지가 갱신되는 시점 차이로 본다 (실제 로그에서 108번, 대부분 1~5행)
--   [열림 중 전류] 접촉기 신호가 0 인데 |인버터 전류| > 5 A 인 행 (접촉기가 정말 열렸다면 불가능)
-- 깨진 행을 먼저 빼는 이유: 한 줄 손상 행은 접촉기 신호까지 0 으로 채워져(실제 로그 31번) 가짜 '열림 -> 닫힘'을 만든다.
WITH c AS (
    SELECT session_id, row_no, motor_main_contactor AS mc, inv_voltage, bms_voltage, inv_dc_current, bms_current,
           LAG(motor_main_contactor) OVER w AS prev_mc,
           LAG(row_no) OVER w AS prev_row
    FROM sample_clean
    WINDOW w AS (PARTITION BY session_id ORDER BY row_no)
),
closure AS (                    -- 접촉기 닫힘 순간
    SELECT session_id, row_no, inv_voltage / NULLIF(bms_voltage, 0) AS ratio
    FROM c WHERE mc = 1 AND prev_mc = 0
),
mm AS (                         -- 전류 불일치 행을 이어진 덩어리로 묶기 (gaps and islands)
    SELECT session_id, row_no, row_no - ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY row_no) AS grp
    FROM c WHERE inv_dc_current > 25 AND bms_current <= 0.5
),
mm_run AS (
    SELECT session_id, grp, COUNT(*) AS n FROM mm GROUP BY session_id, grp
)
SELECT se.label AS 세션,
       (SELECT COUNT(*) FROM closure x WHERE x.session_id = se.session_id) AS 접촉기_닫힘,
       (SELECT ROUND(MIN(ratio), 3) FROM closure x WHERE x.session_id = se.session_id) AS 닫힐때_전압비_최소,
       (SELECT COUNT(*) FROM closure x WHERE x.session_id = se.session_id AND (ratio < 0.90 OR ratio IS NULL)) AS 프리차지_미달,
       (SELECT COUNT(*) FROM mm_run r WHERE r.session_id = se.session_id AND n >= 10) AS 전류_불일치,
       (SELECT COALESCE(MAX(n), 0) FROM mm_run r WHERE r.session_id = se.session_id) AS 불일치_최장_행,
       (SELECT COUNT(*) FROM c WHERE c.session_id = se.session_id AND mc = 0 AND ABS(inv_dc_current) > 5) AS 열림중_전류_행
FROM session se
ORDER BY se.session_id;
