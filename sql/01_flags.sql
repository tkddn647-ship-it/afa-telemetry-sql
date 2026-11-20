-- 앞뒤 행과 비교해 깨진 값을 표시하는 뷰.
-- 세션의 첫 행·마지막 행처럼 비교할 이웃이 없으면 0(정상)으로 둔다.
-- 규칙: 값 하나만 앞뒤 둘 다와 크게 다르고, 앞뒤끼리는 서로 가까우면 '튄 값'으로 본다.
--   stm_ms          : 앞뒤와 1000 ms 넘게 차이, 앞뒤 간격은 0~200 ms  (글자가 빠지거나 끼어든 시각)
--   inv_dc_current  : 앞뒤와 200 A 넘게 차이, 앞뒤 차이 100 A 미만
--   bms_current     : 앞뒤와 100 A 넘게 차이, 앞뒤 차이  50 A 미만
--   vehicle_speed   : 앞뒤와 30 km/h 넘게 차이(10 ms 안에 불가능), 앞뒤 차이 15 km/h 미만
DROP VIEW IF EXISTS sample_flags;
CREATE VIEW sample_flags AS
WITH w AS (
    SELECT s.*,
           LAG(stm_ms)  OVER o AS p_ms,  LEAD(stm_ms)  OVER o AS n_ms,
           LAG(inv_dc_current) OVER o AS p_inv, LEAD(inv_dc_current) OVER o AS n_inv,
           LAG(bms_current)    OVER o AS p_bms, LEAD(bms_current)    OVER o AS n_bms,
           LAG(vehicle_speed_kmh)  OVER o AS p_v, LEAD(vehicle_speed_kmh) OVER o AS n_v
    FROM sample s
    WINDOW o AS (PARTITION BY session_id ORDER BY row_no)
)
SELECT w.*,
    COALESCE((ABS(stm_ms - p_ms) > 1000 AND ABS(stm_ms - n_ms) > 1000 AND n_ms - p_ms BETWEEN 0 AND 200), 0) AS bad_ms,
    COALESCE((ABS(inv_dc_current - p_inv) > 200 AND ABS(inv_dc_current - n_inv) > 200 AND ABS(n_inv - p_inv) < 100), 0) AS bad_inv,
    COALESCE((ABS(bms_current - p_bms) > 100 AND ABS(bms_current - n_bms) > 100 AND ABS(n_bms - p_bms) < 50), 0) AS bad_bms,
    COALESCE((ABS(vehicle_speed_kmh - p_v) > 30 AND ABS(vehicle_speed_kmh - n_v) > 30 AND ABS(n_v - p_v) < 15), 0) AS bad_speed
FROM w;
