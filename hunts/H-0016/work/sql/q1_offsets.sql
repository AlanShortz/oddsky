-- AllWISE (2010) vs NEOWISE 2014-15 baseline: offset as a function of magnitude, quiet stars only
SELECT ROUND(w1mpro_allwise*2)/2 AS w1bin,
       COUNT(*) n,
       APPROX_QUANTILES(w1_base - w1mpro_allwise, 100)[OFFSET(50)] AS d1_med,
       APPROX_QUANTILES(w1_base - w1mpro_allwise, 100)[OFFSET(16)] AS d1_p16,
       APPROX_QUANTILES(w1_base - w1mpro_allwise, 100)[OFFSET(84)] AS d1_p84,
       APPROX_QUANTILES(w2_base - w2mpro_allwise, 100)[OFFSET(50)] AS d2_med,
       APPROX_QUANTILES(w2_base - w2mpro_allwise, 100)[OFFSET(16)] AS d2_p16,
       APPROX_QUANTILES(w2_base - w2mpro_allwise, 100)[OFFSET(84)] AS d2_p84,
       COUNTIF(ABS(w1_base - w1mpro_allwise) > 0.5 AND ABS(w2_base - w2mpro_allwise) > 0.5) AS n_step05,
       COUNTIF(ABS(w1_base - w1mpro_allwise) > 1.0 AND ABS(w2_base - w2mpro_allwise) > 1.0) AS n_step10
FROM `oddsky-sky-br3c3.sky.sky2_features`
WHERE n_visits >= 12 AND w1_ptp < 0.3 AND w2_ptp < 0.3 AND base_std_w2 < 0.1
  AND w1mpro_allwise IS NOT NULL AND w2mpro_allwise IS NOT NULL AND w1_base IS NOT NULL AND w2_base IS NOT NULL
GROUP BY w1bin ORDER BY w1bin
