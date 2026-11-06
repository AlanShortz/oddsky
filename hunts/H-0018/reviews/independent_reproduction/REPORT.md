# Independent reproduction, 2026-11-06

A separate agent wrote its own code (`part1.py`–`part5.py`, here unchanged), was told not to read `hunts/H-0018`, and was given the
definitions of the statistics but no interpretation and no results. All-sample figures, dev and held-out together.

**Sign.** s = sign(BF − AG), derived from the Thiele-Innes model. Checks: east × north = +n̂ at 1000 random positions; a time-domain
Kepler test agreed 2000/2000; BF − AG = −a² cos i; Gaia BH1 s = +1 (i = 121°) and BH2 s = −1 (i = 35°).

**A overall** −0.0781 ± 0.0024, N = 168,065 (Orbital −0.0877, AstroSpectroSB1 −0.0397).

| P from (d) | N | A | ± | ratio | ± |
|---|---|---|---|---|---|
| 50 | 1039 | +.153 | .031 | .862 | .039 |
| 100 | 3557 | −.006 | .017 | .997 | .017 |
| 150 | 5267 | +.080 | .014 | .948 | .009 |
| 200 | 9354 | +.009 | .010 | .996 | .007 |
| 250 | 10313 | +.006 | .010 | 1.035 | .007 |
| 300 | 4923 | −.150 | .014 | 1.084 | .018 |
| 340 | 1225 | −.282 | .027 | 1.164 | .046 |
| 390 | 8660 | −.136 | .011 | 1.103 | .012 |
| 450 | 13099 | −.079 | .009 | 1.103 | .009 |
| 500 | 29335 | −.059 | .006 | 1.075 | .005 |
| 600 | 22929 | −.117 | .007 | 1.212 | .009 |
| 700 | 16760 | −.144 | .008 | 1.300 | .011 |
| 800 | 14885 | −.105 | .008 | 1.187 | .010 |
| 900 | 11283 | −.094 | .009 | 1.149 | .010 |
| 1000 | 6307 | −.084 | .013 | 1.170 | .014 |
| 1100 | 5046 | −.067 | .014 | 1.175 | .018 |
| 1300 | 2250 | −.056 | .021 | 1.204 | .025 |
| 1600 | 1556 | −.066 | .025 | 1.228 | .043 |

**Dipole on orbits** (HC3 errors): constant +.0050 ± .0025; X +.0020 ± .0044, Y −.1085 ± .0036, Z −.0184 ± .0054. Angle to NGP 99.6°, to NEP 159.2°.

**Wide pairs** (dev + held-out; N = 122,901 of 584,803; HC3 errors): constant +.0022 ± .0029; X +.0007 ± .0048, Y −.0044 ± .0045, Z −.0143 ± .0057.
Bins: 10²–10³ au Z −.0099 ± .0125; 10³–10⁴ Z −.0178 ± .0068; 10⁴–3×10⁴ Z −.0141 ± .0233; 3×10⁴–10⁵ Z +.1770 ± .0632 (N = 1001).

**Hemispheres.** mean(s | north) = −.0743 ± .0035, mean(s | south) = +.0817 ± .0034. All-sky mean(s) = +.0064 ± .0024.

**Other checks found clean.** ecl_lat agrees with ra/dec to ≤ 0.03″ with no sign mismatch; no duplicates; swapping stars leaves z's sign unchanged.

**Reached on its own, unprompted.**
- A Fisher simulation with a nominal scan law and free P, e, T gives σ_ϖ(+)/σ_ϖ(−) = 1.29 at 730 d and 1.75 at 365 d. The ratio is exactly 1 with no P, e, T columns and inverts (0.71, 0.61) when Earth's orbit is reversed. It survives random scan angles.
- Orbital solutions obey parallax_over_error > 20000/P with none below.
- A against a sense-blind margin, 300–1100 d: [0,1) −.361 ± .013; [1,1.5) −.192; [2,3) −.057; pooled ≥ 3 −.033 ± .006.
- Mock against observed A: Spearman .93, mean −.032 against −.074.

**Not explained there.** The residual −.033; at P > 1100 d the mock A ≈ 0 against −.06 to −.09 and simulated ratio 1.01–1.05 against about 1.15–1.19; at 50–100 d, +.019 against +.197. A noise-only simulation of fitted Thiele-Innes constants gives mean sense +.69 at 365 d, about +.11 at 320 and 420 d, −.07 at 183 d, ≤ .03 at ≥ 550 d, opposite in sign to the observed A near one year.
