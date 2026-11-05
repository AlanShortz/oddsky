SELECT
  COUNTIF(color_base >= 0.4 AND w1_base BETWEEN 9 AND 15 AND w2_base <= 14) AS red_after,
  COUNTIF(color_base >= 0.4 AND w1_base BETWEEN 9 AND 15 AND w2_base <= 14 AND w1_ptp < 0.4 AND w2_ptp < 0.4) AS red_after_quiet,
  COUNTIF((w1mpro_allwise - w2mpro_allwise) >= 0.4 AND w1mpro_allwise BETWEEN 9 AND 15 AND w2mpro_allwise <= 14) AS red_2010,
  COUNTIF((w1mpro_allwise - w2mpro_allwise) >= 0.4 AND w1mpro_allwise BETWEEN 9 AND 15 AND w2mpro_allwise <= 14 AND w1_ptp < 0.4 AND w2_ptp < 0.4) AS red_2010_quiet,
  COUNTIF((w1mpro_allwise - w2mpro_allwise) >= 0.4 AND w1mpro_allwise BETWEEN 9 AND 15 AND w2mpro_allwise <= 14 AND color_base < 0.4) AS red_2010_blue_after,
  COUNTIF((w1mpro_allwise - w2mpro_allwise) >= 0.4 AND w1mpro_allwise BETWEEN 9 AND 15 AND w2mpro_allwise <= 14 AND color_base < 0.4 AND w1_ptp < 0.4 AND w2_ptp < 0.4) AS red_2010_blue_after_quiet
FROM `oddsky-sky-br3c3.sky.sky2_features`
WHERE n_visits >= 12
