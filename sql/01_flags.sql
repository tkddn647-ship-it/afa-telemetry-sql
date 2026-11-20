-- 깨진 값을 표시하는 뷰 (규칙 v2, 2026-11-20).
-- 세션의 첫 행·마지막 행처럼 비교할 이웃이 없으면 0(정상)으로 둔다.
--
-- [시각] stm_ms: 앞뒤와 1000 ms 넘게 차이, 앞뒤 간격은 0~200 ms (글자가 빠지거나 끼어든 시각)
--        깨진 시각이 두 행 연달아 나오는 경우도 있어(오후1차 11419·11420행) 한 칸 건너 이웃과도 비교한다
-- [값]   모든 숫자 열 30개: |값 - 앞뒤 2행씩 5행 중앙값| > min_dev (value_check 표). 결과는 value_flag 표 (sql/01a)
--        규칙 v1(인버터 200 A, 팩 100 A, 속도 30 km/h, 앞뒤 한 행씩 비교)은 두 행 연달아 튄 값을 크기와 상관없이 못 잡았다
--        (eval_models.py). v1 판정도 그대로 남겨 OR로 합친다 (v1이 잡던 것을 잃지 않게).
-- bad_inv / bad_bms / bad_speed : 그 열의 값을 믿을 수 없음 (v1 규칙 OR 값 검사)
-- bad_value                      : 검사한 30열 중 하나라도 튄 값
-- n_bad_cols                     : 이 행에서 튄 열 수. 3 이상이면 한 줄 전체가 밀리거나 깨진 것으로 보인다 (README 6-3)
DROP VIEW IF EXISTS sample_flags;
CREATE VIEW sample_flags AS
WITH w AS (
    SELECT s.*,
           LAG(stm_ms)  OVER o AS p_ms,  LEAD(stm_ms)  OVER o AS n_ms,
           LAG(stm_ms, 2) OVER o AS p2_ms, LEAD(stm_ms, 2) OVER o AS n2_ms,
           LAG(inv_dc_current) OVER o AS p_inv, LEAD(inv_dc_current) OVER o AS n_inv,
           LAG(bms_current)    OVER o AS p_bms, LEAD(bms_current)    OVER o AS n_bms,
           LAG(vehicle_speed_kmh)  OVER o AS p_v, LEAD(vehicle_speed_kmh) OVER o AS n_v
    FROM sample s
    WINDOW o AS (PARTITION BY session_id ORDER BY row_no)
), vf AS (
    SELECT session_id, row_no, COUNT(*) AS n_bad_cols,
           MAX(column_name = 'inv_dc_current') AS vf_inv,
           MAX(column_name = 'bms_current') AS vf_bms,
           MAX(column_name = 'vehicle_speed_kmh') AS vf_speed
    FROM value_flag
    GROUP BY session_id, row_no
)
SELECT w.*,
    COALESCE((ABS(stm_ms - p_ms) > 1000 AND ABS(stm_ms - n_ms) > 1000 AND n_ms - p_ms BETWEEN 0 AND 200), 0)
     OR COALESCE((ABS(stm_ms - p_ms) > 1000 AND ABS(stm_ms - n2_ms) > 1000 AND n2_ms - p_ms BETWEEN 0 AND 300), 0)
     OR COALESCE((ABS(stm_ms - p2_ms) > 1000 AND ABS(stm_ms - n_ms) > 1000 AND n_ms - p2_ms BETWEEN 0 AND 300), 0) AS bad_ms,
    COALESCE((ABS(inv_dc_current - p_inv) > 200 AND ABS(inv_dc_current - n_inv) > 200 AND ABS(n_inv - p_inv) < 100), 0)
     OR COALESCE(vf.vf_inv, 0) AS bad_inv,
    COALESCE((ABS(bms_current - p_bms) > 100 AND ABS(bms_current - n_bms) > 100 AND ABS(n_bms - p_bms) < 50), 0)
     OR COALESCE(vf.vf_bms, 0) AS bad_bms,
    COALESCE((ABS(vehicle_speed_kmh - p_v) > 30 AND ABS(vehicle_speed_kmh - n_v) > 30 AND ABS(n_v - p_v) < 15), 0)
     OR COALESCE(vf.vf_speed, 0) AS bad_speed,
    vf.n_bad_cols IS NOT NULL AS bad_value,
    COALESCE(vf.n_bad_cols, 0) AS n_bad_cols
FROM w LEFT JOIN vf USING (session_id, row_no);

-- 깨진 값이 하나도 없는 행만 모은 뷰
DROP VIEW IF EXISTS sample_clean;
CREATE VIEW sample_clean AS
SELECT * FROM sample_flags WHERE NOT (bad_ms OR bad_inv OR bad_bms OR bad_speed OR bad_value);
