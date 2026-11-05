-- control for the 2010 fading test: AGN-coloured, quiet sources in the same magnitude window that did NOT change across the gap
SELECT allwise_cntr, n_visits, w1_base, w2_base, color_base, t_first, t_last, w1_ptp, w2_ptp, w2_end, color_end, w2_rise, w1_rise, t_rise, w2_rise_sigma,
       w1mpro_allwise, w2mpro_allwise
FROM `oddsky-sky-br3c3.sky.sky2_features`
WHERE n_visits >= 12 AND w1_ptp < 0.4 AND w2_ptp < 0.4
  AND w1mpro_allwise BETWEEN 9 AND 15 AND w2mpro_allwise BETWEEN 12.5 AND 14
  AND (w1mpro_allwise - w2mpro_allwise) >= 0.4
  AND ABS(w1_base - w1mpro_allwise) < 0.1 AND ABS(w2_base - w2mpro_allwise) < 0.1
  AND MOD(ABS(FARM_FINGERPRINT(CAST(allwise_cntr AS STRING))), 2000) = 7
LIMIT 400
