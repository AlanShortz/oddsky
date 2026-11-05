-- nuclei that cooled: AGN-coloured in AllWISE (2010-11), fainter and bluer in the NEOWISE 2014-15 baseline, quiet 2014-2024
SELECT allwise_cntr, n_visits, w1_base, w2_base, color_base, w1_ptp, w2_ptp, w1mpro_allwise, w2mpro_allwise, w3mpro_allwise, w4mpro_allwise, pixel,
       w1_base - w1mpro_allwise AS d1, w2_base - w2mpro_allwise AS d2,
       (w1mpro_allwise - w2mpro_allwise) - color_base AS dcolor
FROM `oddsky-sky-br3c3.sky.sky2_features`
WHERE n_visits >= 12 AND w1_ptp < 0.4 AND w2_ptp < 0.4
  AND w1mpro_allwise BETWEEN 9 AND 15 AND w2mpro_allwise <= 14
  AND (w1mpro_allwise - w2mpro_allwise) >= 0.4
  AND (w1_base - w1mpro_allwise) > 0.3 AND (w2_base - w2mpro_allwise) > 0.5
  AND (w1mpro_allwise - w2mpro_allwise) - color_base >= 0.25
