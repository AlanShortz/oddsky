SELECT pixel, COUNT(*) n,
  APPROX_QUANTILES(w1_base - w1mpro_allwise, 100)[OFFSET(50)] d1_med,
  APPROX_QUANTILES(w1_base - w1mpro_allwise, 100)[OFFSET(5)] d1_p05,
  APPROX_QUANTILES(w1_base - w1mpro_allwise, 100)[OFFSET(95)] d1_p95,
  COUNTIF(ABS(w1_base - w1mpro_allwise) > 0.4 AND ABS(w2_base - w2mpro_allwise) > 0.4) n_step,
  APPROX_QUANTILES(n_visits, 100)[OFFSET(50)] nv_med
FROM `oddsky-sky-br3c3.sky.sky2_features`
WHERE n_visits >= 12 AND w1_ptp < 0.3 AND w2_ptp < 0.3 AND base_std_w2 < 0.1 AND w1mpro_allwise BETWEEN 8 AND 14.5 AND w2mpro_allwise <= 13.5
  AND pixel IN (11810, 11816, 1684, 1570, 1568, 10783, 3199, 11649, 11601, 3353, 1720, 5176, 5000, 6000, 7000, 8000, 2000, 9000)
GROUP BY pixel ORDER BY pixel
