-- Q1
SELECT label, row_count FROM session ORDER BY session_id;
-- Q2
SELECT COUNT(*) FROM sample WHERE vehicle_speed_kmh > 60;
-- Q3
SELECT session_id, MAX(vehicle_speed_kmh), ROUND(AVG(bms_voltage), 1)
FROM sample GROUP BY session_id ORDER BY session_id;
-- Q4
SELECT session_id, COUNT(*) FROM sample WHERE inv_dc_current > 25
GROUP BY session_id HAVING COUNT(*) >= 1000 ORDER BY session_id;
-- Q5
SELECT se.label, COUNT(*) FROM sample s JOIN session se USING (session_id)
WHERE s.inv_dc_current > 25 GROUP BY s.session_id HAVING COUNT(*) >= 1000 ORDER BY s.session_id;
-- Q6
SELECT s.session_id, ROUND(AVG(s.bms_current * c.factor), 2)
FROM sample s JOIN scale_correction c ON c.column_name = 'bms_current'
WHERE s.inv_dc_current > 25 GROUP BY s.session_id ORDER BY s.session_id;
-- Q7
SELECT session_id, COUNT(*) FROM sample
WHERE vehicle_speed_kmh > (SELECT AVG(vehicle_speed_kmh) FROM sample)
GROUP BY session_id ORDER BY session_id;
-- Q8
WITH load AS (SELECT session_id, bms_current / inv_dc_current AS r FROM sample WHERE inv_dc_current > 25)
SELECT session_id, ROUND(AVG(r), 3) FROM load GROUP BY session_id ORDER BY session_id;
-- Q9
WITH g AS (SELECT stm_ms - LAG(stm_ms) OVER (PARTITION BY session_id ORDER BY row_no) AS d FROM sample)
SELECT d, COUNT(*) AS n FROM g WHERE d IS NOT NULL GROUP BY d ORDER BY n DESC LIMIT 5;
-- Q10
WITH r AS (
  SELECT session_id, bms_current / inv_dc_current AS v,
         ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY bms_current / inv_dc_current) AS rn,
         COUNT(*) OVER (PARTITION BY session_id) AS n
  FROM sample WHERE inv_dc_current > 25)
SELECT session_id, ROUND(AVG(v), 3) FROM r WHERE rn IN ((n+1)/2, (n+2)/2) GROUP BY session_id ORDER BY session_id;
-- Q11
WITH l AS (
  SELECT session_id, row_no - ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY row_no) AS grp
  FROM sample WHERE inv_dc_current > 25),
seg AS (SELECT session_id, grp, COUNT(*) AS len FROM l GROUP BY session_id, grp)
SELECT session_id, COUNT(*), MAX(len) FROM seg GROUP BY session_id ORDER BY session_id;
-- Q12
WITH a AS (SELECT session_id, COUNT(*) n, SUM(inv_dc_current) sx, SUM(bms_current) sy,
                  SUM(inv_dc_current*inv_dc_current) sxx, SUM(inv_dc_current*bms_current) sxy
           FROM sample WHERE inv_dc_current > 25 GROUP BY session_id)
SELECT session_id, ROUND((n*sxy - sx*sy) / (n*sxx - sx*sx), 3) FROM a ORDER BY session_id;
