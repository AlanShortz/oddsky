-- Hunt H-0002 queries over the full-sky NEOWISE pass (BigQuery external tables on the private bucket).
-- Tables: `oddsky-sky-br3c3.sky.sky1_features` (one row per AllWISE star, |b| >= 10 deg + pixel 9840).

-- 1. Census: how many stars did we actually test?
SELECT COUNT(*) AS stars, COUNTIF(n_visits >= 8) AS well_sampled,
       COUNTIF(n_visits >= 8 AND ABS(color_base) < 0.15 AND base_scatter_w2 < 0.05 AND w1_base < 13.5) AS testable_photospheres,
       COUNTIF(afterglow) AS afterglow_flags
FROM `oddsky-sky-br3c3.sky.sky1_features`;

-- 2. Background: distribution of the sustained W2 rise among testable photospheres (false-positive tail).
SELECT ROUND(w2_rise, 2) AS rise, COUNT(*) AS n
FROM `oddsky-sky-br3c3.sky.sky1_features`
WHERE n_visits >= 8 AND ABS(color_base) < 0.15 AND base_scatter_w2 < 0.05 AND w1_base < 13.5 AND w2_rise > 0.1
GROUP BY rise ORDER BY rise;

-- 3. Vanishing dust: an infrared excess at the start that faded back toward a bare photosphere
--    (cf. TYC 8241 2652 1, Melis et al. 2012).
SELECT pixel, allwise_cntr, n_visits, w1_base, w2_base, color_base, color_end, w2_end, w1mpro_allwise, w3mpro_allwise, w4mpro_allwise
FROM `oddsky-sky-br3c3.sky.sky1_features`
WHERE n_visits >= 12 AND base_scatter_w2 < 0.05 AND w1_base < 13 AND color_base > 0.25
  AND color_end - color_base < -0.2 AND w2_end > 0.2
ORDER BY (color_end - color_base) ASC
LIMIT 200;
