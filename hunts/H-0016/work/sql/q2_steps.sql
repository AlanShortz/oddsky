SELECT allwise_cntr, n_visits, w1_base, w2_base, color_base, base_std_w2, t_first, t_last, w1_ptp, w2_ptp, w2_med_err,
       base_scatter_w2, w2_rise, w1_rise, t_rise, w2_end, color_end, w1mpro_allwise, w2mpro_allwise, w3mpro_allwise, w4mpro_allwise, pixel, afterglow,
       w1_base - w1mpro_allwise AS d1, w2_base - w2mpro_allwise AS d2
FROM `oddsky-sky-br3c3.sky.sky2_features`
WHERE n_visits >= 12 AND w1_ptp < 0.3 AND w2_ptp < 0.3 AND base_std_w2 < 0.1
  AND w1mpro_allwise BETWEEN 8 AND 14.5 AND w2mpro_allwise <= 13.5
  AND w1_base IS NOT NULL AND w2_base IS NOT NULL
  AND ABS(w1_base - w1mpro_allwise) > 0.4 AND ABS(w2_base - w2mpro_allwise) > 0.4
  AND SIGN(w1_base - w1mpro_allwise) = SIGN(w2_base - w2mpro_allwise)
