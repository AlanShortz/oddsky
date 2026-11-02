# H-0014 Gaia DR3 run (dry run: stand-in release)

Generated 2026-11-02 20:51 UTC. Outputs: `/Users/alanshortz/oddsky-runs/h0014/dr3`.

| stage | ok | seconds | key results |
|---|---|---|---|
| probe | yes | 134.1 | {"probe_ok": true, "fixes": [], "epoch_layout": "dr3", "retrieval_types": ["EPOCH_PHOTOMETRY", "MCMC_GSPPHOT", "MCMC_MSC"]} |
| readiness | yes | 7.8 | {"summary": "15 Gaia predictions checked against Gaia DR3; gradable now: 0; waiting for a later release by design: 10; identity doubts: 0; provisional true/false: 0/0; Gaia DR3 request failed: False", "release_failed": false} |
| idmap | yes | 37.5 | {"n": 2647, "changed": 2, "unmatched": 408} |
| ensemble | yes | 5.1 | {"grade": {"exit": 0, "tail": ["PASS 0 of 47 testable-by-design events (0 resolved; 47 untestable for lack of data)", "forecast (all 47): 8.9 passes expected of 47 (median 8, 80% 5-14, 90% 4-15)", "no event resolved: nothing to grade (check the DR4 fetch, the id map and the column mapping)"]}, "selftest": {"exit": 0, "tail": ["sliding control (fake event every 5 d, >= 180 d from the event): 0 passes in 181 testable trials (227 others had too few transits)", "", "self-test: PASS (all three DR3-confirmed events pass; no control passes)"]}, "status_counts": {"untestable (data)": 47}} |
| catalogue | yes | 174.4 | {"lens_catalogue": 363, "classifier_only": 254, "target_flags": 2647, "target_classes": 875, "cones": 7, "classifier_only_not_in_catalogue": 67, "h0010_list_reproduced": {"same": 67, "only_h0010": 0, "only_release": 0}, "targets_in_release_lens_catalogue": {}, "release_lenses_unreported": 0, "release_lenses_with_neowise_event": 25} |
| epochs | yes | 0.5 | {"status": [{"tier": 1, "status": "absent", "n": 106}, {"tier": 1, "status": "ok", "n": 73}, {"tier": 2, "status": "absent", "n": 1740}, {"tier": 2, "status": "ok", "n": 817}], "chunks": 0, "chunks_failed": 0, "requests": 0} |
| search | yes | 248.3 | {"n_analysed": 896, "labels": {"cases|lens-like brightening": 3, "cases|dip": 2, "cases|deep decline": 1, "cases|high-scatter variable": 1, "cases|periodic large-amplitude variable": 1, "cases|quiet": 1, "h0010|lens-like brightening": 50, "h0010|chromatic brightening": 8, "h0010|brightening, not lens-shaped": 6, "h0010|one-date brightening (scan-angle artifact possible)": 1, "h0010|quiet": 1, "h0010|repeating brightenings": 1, "rcb|periodic large-amplitude variable": 505, "rcb|high-scatter variable": 158, "rcb|quiet": 67, "rcb|deep decline": 17, "rcb|dip": 16, "rcb|repeating brightenings": 14, |

## Top of the ranked list (not known to any catalogue we hold; triage, not claims)

| priority | set | name | source_id | label | gaia_class | vsx | A_obs_G | dG_fade | t_peak | t_event | ev_status | colour | ls_period | ls_power | lens_tE | dbic_shape_minus_lens |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | h0010 | J182811.16-082538.6 | 4156259162525506816 | lens-like brightening | MICROLENSING | none | 9.14 |  | 57300.23 |  |  | untested |  |  | 73.8 | 1.2 |
| 1 | h0010 | J180157.93-174159.6 | 4143778198039891712 | lens-like brightening | MICROLENSING | none | 6.668 |  | 57877.27 |  |  | untested | 22.3 | 0.756 | 223.7 | 2.4 |
| 1 | h0010 | J171234.40-353502.0 | 5977088149415668736 | lens-like brightening | MICROLENSING | none | 5.848 |  | 57129.89 |  |  | untested | 38.1 | 0.225 | 37.9 | -0.1 |
| 1 | h0010 | J180313.03-150702.0 | 4146782166880069632 | lens-like brightening | MICROLENSING | none | 5.776 |  | 57322.72 |  |  | untested | 21.4 | 0.735 | 108.9 | 10.4 |
| 1 | h0010 | J174618.09-253631.3 | 4067152339419332992 | lens-like brightening | MICROLENSING | none | 4.415 |  | 57106.2 |  |  | achromatic | 45.6 | 0.401 | 27.2 | -6.6 |
| 1 | h0010 | J201826.29+292422.1 | 1861208444041823360 | lens-like brightening | MICROLENSING | none | 4.093 |  | 57468.47 |  |  | untested | 297.1 | 0.097 | 43.7 | 2.2 |
| 1 | h0010 | J174029.07-331407.7 | 4054091653004081408 | lens-like brightening | MICROLENSING | Gaia DR3 4054091648714961152 L 8.8"; Gaia DR3 4054091653004088320 L 9.3" | 3.63 |  | 57793.65 |  |  | untested | 28.7 | 0.574 | 33.2 | 0.8 |
| 1 | h0010 | J151331.38-523733.2 | 5888321552071879552 | lens-like brightening | MICROLENSING | none | 3.563 |  | 56901.53 |  |  | achromatic | 60.2 | 0.319 | 53.5 | -4.1 |
| 1 | h0010 | J154718.28-560218.3 | 5884091589077519616 | lens-like brightening | MICROLENSING | none | 3.231 |  | 56902.2 |  |  | untested | 102.8 | 0.357 | 130.6 | -0.7 |
| 1 | h0010 | J174036.98-223251.4 | 4117136992643758080 | lens-like brightening | MICROLENSING | none | 3.145 |  | 57790.58 |  |  | untested | 43.2 | 0.306 | 15.9 | -4.4 |
| 1 | h0010 | J172020.30-381044.3 | 5972789089004520192 | lens-like brightening | MICROLENSING | none | 3.083 |  | 57690.25 |  |  | untested | 33.7 | 0.679 | 132.5 | 4.7 |
| 1 | h0010 | J182656.25-264645.9 | 4052046905029445376 | lens-like brightening | MICROLENSING | none | 3.032 |  | 57131.95 |  |  | untested | 53.5 | 0.379 | 48.3 | -2.3 |
| 1 | h0010 | J190032.43-004939.8 | 4265542994777483776 | lens-like brightening | MICROLENSING | none | 2.617 |  | 57129.68 |  |  | untested | 54.4 | 0.72 | 48.7 | -1.4 |
| 1 | h0010 | J173332.42-421445.1 | 5958944416543307648 | lens-like brightening | MICROLENSING | none | 2.481 |  | 56907.78 |  |  | achromatic | 27.4 | 0.591 | 241.1 | 32.3 |
| 1 | h0010 | J175414.32-275241.8 | 4063479523864717184 | lens-like brightening | MICROLENSING | Gaia DR3 4063479523864704128 L 8.3" | 2.372 |  | 57693.76 |  |  | untested | 103.9 | 0.411 | 14.9 | -0.7 |
| 1 | h0010 | J171838.94-334129.2 | 5979167630832540032 | lens-like brightening | MICROLENSING | none | 2.339 |  | 57689.93 |  |  | untested | 29.4 | 0.325 | 49.5 | -0.8 |
| 1 | h0010 | J183932.79-140259.3 | 4103794114069593216 | lens-like brightening | MICROLENSING | none | 2.272 |  | 57678.95 |  |  | untested | 27.3 | 0.822 | 93.6 | -1 |
| 1 | h0010 | J174656.42-190909.2 | 4119926316171065984 | lens-like brightening | MICROLENSING | none | 2.13 |  | 57077.46 |  |  | achromatic | 49.2 | 0.48 | 105.3 | 12640.5 |
| 1 | h0010 | J072830.43-204112.5 | 5620272814897694848 | lens-like brightening | MICROLENSING | none | 1.713 |  | 57072.55 |  |  | achromatic | 384.2 | 0.279 | 269 | 217.4 |
| 1 | h0010 | J184837.12-051620.2 | 4254872092666139264 | lens-like brightening | MICROLENSING | none | 1.559 |  | 57828.6 |  |  | untested | 62.8 | 0.65 | 106.5 | 1303.1 |
| 1 | h0010 | J174929.70-363245.6 | 4040204305809966848 | lens-like brightening | MICROLENSING | none | 1.469 |  | 57877.78 |  |  | untested | 22 | 0.478 | 36.2 | -0.8 |
| 1 | h0010 | J200958.93+321427.9 | 2054828730840779520 | lens-like brightening | MICROLENSING | none | 1.444 |  | 57371.89 |  |  | untested | 55.1 | 0.201 | 38.6 | 296.3 |
| 1 | h0010 | J182124.77-190909.7 | 4096047127002546560 | lens-like brightening | MICROLENSING | none | 1.443 |  | 57271.49 |  |  | achromatic | 29.9 | 0.699 | 269.4 | 14.8 |
| 1 | h0010 | J182539.91-125139.3 | 4152593734345648000 | lens-like brightening | MICROLENSING | none | 1.346 |  | 57102.45 |  |  | untested | 26.9 | 0.508 | 40.2 | -5.4 |
| 1 | h0010 | J185315.30+003122.8 | 4266315436092309504 | lens-like brightening | MICROLENSING | none | 1.258 |  | 56918.55 |  |  | untested | 29.4 | 0.633 | 65.9 | -0.8 |
| 2 | rcb | GDR3-198809985981609600 | 198809985981609600 | deep decline |  | Gaia DR3 198809985981609600 VAR 0.0" |  | 1.811 |  |  |  |  | 58.5 | 0.175 |  |  |
| 3 | rcb | T20-2541 | 4119606289572719488 | lens-like brightening | LPV | Gaia DR3 4119606289572719488 L 0.1" | 3.53 |  | 57866.09 |  |  | untested |  |  | 200.6 | -6.9 |
| 3 | rcb | T20-2489 | 4149054994869557760 | lens-like brightening | LPV | Gaia DR3 4149054994869557760 L 0.0" | 1.515 |  | 56912.72 |  |  | achromatic | 102.4 | 0.656 | 102.2 | 232.3 |
| 3 | rcb | T20-2600 | 4043097430124988288 | lens-like brightening; deep decline | LPV | OGLE-BLG-LPV-202595 M 0.2" | 1.419 | 1.332 | 57268.48 |  |  | untested |  |  | 10.2 | -1.6 |
| 3 | rcb | T20-7014 | 4650201842031681280 | lens-like brightening | LPV | Gaia DR3 4650201842031681280 L 0.0" | 1.215 |  | 56935.05 |  |  | untested | 30.8 | 0.59 | 116.9 | 157.6 |
| 4 | rcb | T20-2514 | 4041843776378419072 | one-date brightening (scan-angle artifact possible); deep decline | LPV | OGLE-BLG-LPV-049557 M 0.1" | 14.8 | 2.254 | 56909.79 |  |  | untested | 405.9 | 0.553 | 47.6 | -2.1 |
| 4 | h0010 | J144905.72-545455.6 | 5893807634053861120 | brightening, not lens-shaped | MICROLENSING | none | 13.974 |  | 57045.69 |  |  | untested | 22.7 | 0.652 | 91.9 | -21.6 |
| 4 | h0010 | J184922.92-000203.9 | 4266365704324232576 | brightening, not lens-shaped | MICROLENSING | none | 7.431 |  | 57703.7 |  |  | untested | 162.9 | 0.826 | 119 | -31.4 |
| 4 | h0010 | J182727.10-153931.2 | 4097904476963000576 | brightening, not lens-shaped | MICROLENSING | none | 3.64 |  | 57078.88 |  |  | untested | 27.8 | 0.703 | 209.5 | -143.3 |
| 4 | rcb | T20-71 | 5440440060304618112 | one-date brightening (scan-angle artifact possible); deep decline | LPV | SSS_J102807.3-405925 LPV 1.6" | 3.594 | 1.651 | 56875.94 |  |  | untested | 316.9 | 0.581 | 76 | -15.3 |
| 4 | h0010 | J171847.68-300609.5 | 4059204107239408512 | brightening, not lens-shaped | MICROLENSING | none | 1.921 |  | 57781.51 |  |  | untested | 23.6 | 0.471 | 37.2 | -16.8 |
| 4 | rcb | T20-5003 | 4690479156274391936 | deep decline | RCB | Gaia16aau RCB 0.2" |  | 5.385 |  |  |  |  | 20.1 | 0.354 |  |  |
| 4 | rcb | T20-2558 | 4070387922870053376 | deep decline | LPV | Gaia DR3 4070387922870053376 L 0.1" |  | 1.122 |  |  |  |  | 276 | 0.959 |  |  |
| 4 | rcb | T20-2712 | 4257571741608742400 | deep decline | LPV | Gaia DR3 4257571741608742400 L 0.1" |  | 2.38 |  |  |  |  |  |  |  |  |
| 4 | rcb | T20-184 | 4040961521369150720 | deep decline | RCB | ASASSN-V J174257.20-362052.1 RCB 0.1" |  | 5.437 |  |  |  |  | 85.6 | 0.386 |  |  |
