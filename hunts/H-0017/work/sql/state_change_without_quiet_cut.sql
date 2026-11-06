-- how the quiet cut treats the state-changers themselves (referee, 2026-11-05)
SELECT
  COUNTIF(w1mpro_allwise BETWEEN 9 AND 15 AND w2mpro_allwise <= 14 AND (w1mpro_allwise - w2mpro_allwise) >= 0.4
          AND (w1_base - w1mpro_allwise) > 0.3 AND (w2_base - w2mpro_allwise) > 0.5
          AND (w1mpro_allwise - w2mpro_allwise) - color_base >= 0.25) AS cooled_all,
  COUNTIF(w1mpro_allwise BETWEEN 9 AND 15 AND w2mpro_allwise <= 14 AND (w1mpro_allwise - w2mpro_allwise) >= 0.4
          AND (w1_base - w1mpro_allwise) > 0.3 AND (w2_base - w2mpro_allwise) > 0.5
          AND (w1mpro_allwise - w2mpro_allwise) - color_base >= 0.25 AND w1_ptp < 0.4 AND w2_ptp < 0.4) AS cooled_quiet,
  COUNTIF(w1_base BETWEEN 9 AND 15 AND w2_base <= 14 AND color_base >= 0.4
          AND (w1mpro_allwise - w1_base) > 0.3 AND (w2mpro_allwise - w2_base) > 0.5
          AND color_base - (w1mpro_allwise - w2mpro_allwise) >= 0.25) AS heated_all,
  COUNTIF(w1_base BETWEEN 9 AND 15 AND w2_base <= 14 AND color_base >= 0.4
          AND (w1mpro_allwise - w1_base) > 0.3 AND (w2mpro_allwise - w2_base) > 0.5
          AND color_base - (w1mpro_allwise - w2mpro_allwise) >= 0.25 AND w1_ptp < 0.4 AND w2_ptp < 0.4) AS heated_quiet
FROM `oddsky-sky-br3c3.sky.sky2_features`
WHERE n_visits >= 12
