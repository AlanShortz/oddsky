"""s12: the verdicts (written by hand after inspecting every light curve, data/diag_*.png and data/zoom_*.png) and the
robust parameters computed from the fits. Writes hunts/H-0010/work/verdicts.csv; s9_table.py merges it into
work/gaia_ml_unpub.csv.

Verdicts: 'known lens' (in a microlensing catalogue or alert stream within 6" and in time), 'Oddsky case' (found blind by
H-0009, already a case), 'new lens candidate' (P >= 0.4, apparently unreported), 'inconclusive' (0.15 <= P < 0.4),
'not a lens' (P < 0.15, with what it is instead).
Robust parameters only: t0 from the lens model preferred by BIC (+- 3 weeks, from s13) (or a bound when the event is cut by the DR3 window),
tE as the static-fit value scaled by the 16-84% range of fitted/survey tE on the 27 catalogued lenses (s13; the profile
ranges are almost always open because Gaia samples a lens a few times),
the largest observed G ratio (a lower limit on the peak), and the colour test.
Run from the repo root: uv run python -I hunts/H-0010/scripts/s12_verdicts.py"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, WORK, epoch, mjd2date  # noqa: E402

K, C, N, I, X = "known lens", "Oddsky case", "new lens candidate", "inconclusive", "not a lens"

# source_id: (verdict, P(microlensing), known_as / what instead, note)
V = {
    # ---- catalogued lenses (s5: within 6" and in time) ----
    "4043458241772263936": (K, 0.97, "OGLE-2015-BLG-0102 = MOA 2015-BLG-20", "NEOWISE x1.50/x1.56 on 2015-03-20 against the Gaia model's x1.45 (H-0008/H-0009 found it blind; catalogued)"),
    "4062840084877907712": (K, 0.97, "OGLE-2016-BLG-0799 = KMT-2016-BLG-0641", ""),
    "4063409292521568640": (K, 0.97, "OGLE-2016-BLG-0015 = KMT-2016-BLG-0023", ""),
    "4056368634256485504": (K, 0.97, "OGLE-2016-BLG-0004 = KMT-2016-BLG-0321", ""),
    "4049915123787493248": (K, 0.97, "OGLE-2017-BLG-0541 = KMT-2017-BLG-0580", "OGLE tE 15 d: below the catalogue's tE > 20 d cut; peak at the window's end"),
    "4061401893561892608": (K, 0.97, "OGLE-2017-BLG-0078 = KMT-2017-BLG-0772", "baseline G 19.3: fainter than the catalogue's G0 < 19 cut"),
    "4068476460574819584": (K, 0.97, "OGLE-2017-BLG-0259 (also KMT-2016-BLG-2425)", "single scan date in Gaia; Sun 45 deg away at the Gaia peak"),
    "4040875007942475904": (K, 0.97, "OGLE-2015-BLG-0238", ""),
    "4067155397407080064": (K, 0.95, "KMT-2016-BLG-1112", "0.4\" from the KMT position"),
    "4039699492609592704": (K, 0.97, "OGLE-2016-BLG-0338", ""),
    "4068110318885022464": (K, 0.95, "OGLE-2016-BLG-1824", "Gaia colour test fails (k -0.2 +- 0.14): an eclipsing binary 1.9\" away (OGLE-BLG-ECL-079142) shares the BP/RP window"),
    "4063160287489483520": (K, 0.97, "KMT-2016-BLG-0127 = OGLE-2015-BLG-2093", ""),
    "4110560298167203584": (K, 0.97, "OGLE-2015-BLG-1438", ""),
    "4059326835886778240": (K, 0.97, "OGLE-2017-BLG-0114", "OGLE t0 2017-06-15, after DR3 ends"),
    "4064079547909732352": (K, 0.97, "OGLE-2016-BLG-1902 = KMT-2016-BLG-1565", "tE 13-14 d: below the catalogue's tE > 20 d cut"),
    "4116479179755030272": (K, 0.97, "OGLE-2015-BLG-2080", "baseline G 19.7: fainter than G0 < 19"),
    "4043178690980749824": (K, 0.97, "OGLE-2016-BLG-0235 = KMT-2016-BLG-1379", "tE 18-19 d: below tE > 20 d"),
    "4056588845790058368": (K, 0.97, "OGLE-2016-BLG-1886", "x15.5 in Gaia; peak at the window's end"),
    "4089362027543538176": (K, 0.97, "OGLE-2016-BLG-0862", "asymmetric in Gaia: parallax model preferred (chi2 159 vs 171 static)"),
    "4052673351820500480": (K, 0.97, "OGLE-2016-BLG-0086", "NEOWISE x2.24/x2.38 on 2016-03-23 against the Gaia model's x2.44 (H-0009 known lens)"),
    "4062461577902611072": (K, 0.97, "OGLE-2017-BLG-0043", ""),
    "4044193364007000448": (K, 0.9, "KMT-2017-BLG-1499 (same position: KMT-2016-BLG-0336, OGLE-2016-BLG-1765)", "Gaia brightening ~0.25 mag in Jan 2017, below this hunt's episode threshold"),
    "4042386316815947648": (K, 0.97, "OGLE-2015-BLG-0142 = KMT-2016-BLG-1369", "long event (tE 160-220 d in Gaia, 200-240 d OGLE/KMT); a neighbour of equal G within 2\""),
    "4053976376149303552": (K, 0.97, "OGLE-2015-BLG-0196", "OGLE tE 203 d"),
    "4043432227076366592": (K, 0.97, "OGLE-2017-BLG-0329 = KMT-2017-BLG-1105", "peak after DR3 ends"),
    "4041237743668797184": (K, 0.97, "OGLE-2016-BLG-1728", "G only (no BP/RP epochs)"),
    "4050302358026285312": (K, 0.97, "OGLE-2017-BLG-0055 = KMT-2017-BLG-0568", "also VSX ASASSN-V J180510.80-294545.6 (VAR)"),
    "2032454944878107008": (K, 0.99, "Gaia16aye = AT 2016eta (binary lens; Wyrzykowski et al. 2020)", "caustic crossings: no point-lens fit (chi2 5e5); was among the Gaia alerts Wyrzykowski et al. 2023 considered for Sample B"),
    # ---- Oddsky's own cases (H-0009) ----
    "5959812622743175552": (C, 0.65, "OS-0026", "Gaia x6.0, achromatic (k 1.07 +- 0.05); NEOWISE x4.5/x4.8 on 2015-09-07"),
    "4143495279954502016": (C, 0.6, "OS-0027", "Gaia x2.6; NEOWISE x2.69/x2.75 on 2015-09-15 against the Gaia model's x2.91; BP too faint for the colour test"),
    "4145977633638478336": (C, 0.6, "OS-0029", "Gaia x1.5, achromatic (k 1.02 +- 0.05); NEOWISE x1.62/x1.68 against the Gaia model's x1.62"),
    # ---- new candidates ----
    "5958944416543307648": (N, 0.75, "", "NEOWISE x2.43/x2.33 on 2014-09-15, 8 d after Gaia's x2.48 (model x2.29); achromatic in Gaia (k 0.96 +- 0.04); peak before Gaia's first transit, so tE is long but unbounded; outside OGLE EWS coverage; dec -42 (no ZTF). NEOWISE W2 alone reads x7 at one 2017 visit with W1 flat: a single-band artifact, not a repeat"),
    "5620272814897694848": (N, 0.65, "", "Galactic anticentre (l 235). NEOWISE x1.33/x1.35 on 2015-04-10 against the Gaia model's x1.27 (H-0008/H-0009 saw it as a clean but sub-threshold brightening); achromatic in Gaia (k 0.94 +- 0.07) and from G to W2; hot star (GSP-Phot Teff ~8100 K) but no IR excess (W1-W2 -0.04) and no other brightening in NEOWISE 2014-2024 or ZTF 2018-2025, which argues against a Be-star outburst"),
    "5893807634053861120": (N, 0.65, "", "x14 in G, smooth rise and fall over 5 scan dates; parallax model preferred (chi2 46 vs static 76, best shape 53); G 19.9 baseline (BP too faint for colour); no NEOWISE source; south of ZTF; outside OGLE EWS coverage"),
    "2054828730840779520": (N, 0.55, "", "Cygnus (l 70). NEOWISE x1.27/x1.31 on 2015-10-31 against the Gaia model's x1.32; lens beats every non-lens shape by dBIC 78; NEOWISE 2014-2024 and ZTF 2018-2025 show no other brightening; BP/RP noisy (k 0.70 +- 0.37); hot reddened star (GSP-Phot Teff ~9200 K, BP-RP 3.3): a Be-star outburst is the main alternative"),
    "4096047127002546560": (N, 0.5, "", "x1.44 for ~3 months; the AllWISE source 3.0\" away (a blend including this star) brightened ~x1.2 in W1/W2 at +25 d; ZTF 2018-2025 quiet; outside OGLE EWS coverage"),
    "4119926316171065984": (N, 0.5, "", "x2.1, cut by the window start, smooth decline over ~5 months; achromatic within errors (k 0.93 +- 0.16); ZTF 2018-2025 quiet; outside OGLE EWS coverage"),
    "4059204107239408512": (N, 0.5, "", "x1.9 on 2017-01-28 with the Sun 48 deg away (outside the ground bulge season); rise and decline sampled; k 0.90 +- 0.25"),
    "4054091653004081408": (N, 0.5, "", "x3.6 on 2017-02-09 with the Sun 56 deg away, inside OGLE/KMT fields (3 OGLE and 10 KMT events within 15') before their season; G 19.6"),
    "4063479523864717184": (N, 0.5, "", "x2.4 on 2016-11-01 with the Sun 49 deg away, near the Galactic centre (9 OGLE events within 15') after the ground season; G 19.0"),
    "5972789089004520192": (N, 0.5, "", "x3.1 on 2016-10-29 with the Sun 48 deg away; broad (tE ~80-190 d); G 19.2"),
    "4266365704324232576": (N, 0.5, "", "x7.4 on 2016-11-11 with the Sun 57 deg away; parallax model preferred (chi2 23 vs 55); G 20.2, the faintest in the list"),
    "4117136992643758080": (N, 0.5, "", "x3.1 on 2017-02-06 with the Sun 52 deg away; G 19.3; no ZTF source"),
    "1861208444041823360": (I, 0.3, "", "x4.1 on 2016-03-21, ~3-month event, NEOWISE x1.22/x1.18 at +47 d against the Gaia model's x1.33; but a 0.28-mag precursor on 2015-02-17 (2 transits, 10 sigma) and three bright ZTF points (to r 17.9) on 2024 Jan 3-5 in evening twilight 20 deg from the Sun at ZTF's limit: two hints of repeats"),
    "5979167630832540032": (N, 0.45, "", "x2.3 on 2016-10-28 with the Sun 47 deg away; G 19.0"),
    "4265542994777483776": (N, 0.45, "", "x2.6 on 2015-04-17; only 31 epochs; G 19.2; no ZTF source"),
    "5977088149415668736": (N, 0.45, "", "x5.8 on 2015-04-17; rise over 3 scan dates; G 20.1"),
    "4052046905029445376": (N, 0.45, "", "x3.0 on 2015-04-19 (rise on 2 scan dates); b -6.9, outside OGLE EWS coverage"),
    "5888321552071879552": (N, 0.45, "", "x3.6 at Gaia's first transits (2014-09-01), declining; achromatic (k 1.12 +- 0.14); a neighbour 1.4 mag fainter within 2\""),
    "4156259162525506816": (N, 0.45, "", "x9.1, sharp (one month above x2); BP rises more than RP (k 1.76 +- 0.14) but the BP baseline is fainter than 20.5, where Gaia BP is unreliable; ZTF 2018-2025 shows no outburst (a dwarf nova would be the alternative)"),
    "4146782166880069632": (N, 0.4, "", "x5.8 on 2015-10-27; an asymmetric shape fits slightly better (chi2 53 vs 60); BP faint; Sun 57 deg away"),
    "4254872092666139264": (N, 0.4, "", "x1.56 in March 2017 with the decline partly sampled before DR3 ends; ZTF 2018-2025 quiet"),
    # ---- inconclusive ----
    "4152593734345648000": (I, 0.35, "", "x1.35 over ~2 months in 2015; small amplitude; no NEOWISE source; ZTF quiet"),
    "4097904476963000576": (I, 0.3, "", "x3.6 over ~1 year; non-lens shapes fit better (dBIC 45); noisy baseline (0.08 mag)"),
    "4103794114069593216": (I, 0.3, "", "flat-topped x2.3 for ~2 months; noisy (0.09 mag scatter); BP/RP window contaminated (C* 11 sigma)"),
    "4040204305809966848": (I, 0.3, "", "rising x1.47 at DR3's end; no decline"),
    "4120472262420519296": (I, 0.3, "", "rising x2.3 at DR3's end; mildly redder when brighter (dcol +0.12 +- 0.05); BP/RP contaminated (C* 5 sigma); no ZTF source"),
    "4143778198039891712": (I, 0.3, "", "rising x6.7 at DR3's end; a neighbour 0.6 mag fainter within 2\"; no BP/RP colour; no ZTF source"),
    "5884091589077519616": (I, 0.3, "", "declining from x3.2 at Gaia's first transits; G 20.2; few clean epochs"),
    # ---- not lenses ----
    "508920918409038464": (X, 0.01, "artifact: scan-angle-dependent flux of a near-equal pair", "8 one-scan G spikes of 0.4-0.7 mag in 2015-2017, not in BP or RP; a neighbour 0.1 mag fainter within 2\"; BP/RP excess C* 30 sigma; ZTF 2018-2025 flat"),
    "5939477464424988544": (X, 0.03, "artifact: one-scan spike on a blended pair", "x1.6 on a single scan date; two neighbours within 2\"; RUWE 3.6; C* 27 sigma"),
    "2030258876550898816": (X, 0.01, "repeating infrared brightener (Be star or young star)", "Gaia x1.46 in 2015 but NEOWISE x2.95/x3.54 at the same time; NEOWISE again x3.3/x4.1 in May 2019 while ZTF stayed flat; redder when brighter in Gaia (k 0.57 +- 0.06); ESP-HS labels it a hot star"),
    "5861862148375056384": (X, 0.03, "variable infrared source (dusty/young star likely)", "NEOWISE swings 0.7-1.1 mag over 2014-2024 (rms 0.66) and was fainter during Gaia's 'event'"),
    "4266315436092309504": (X, 0.05, "infrared-excess star brightening (Be star or young star likely)", "W1-W2 +0.23; NEOWISE x1.69/x1.99 on 2014-10-06 against Gaia x1.2 (chromatic); redder when brighter in Gaia (k 0.44 +- 0.21)"),
    "5593963735024586240": (X, 0.12, "slow chromatic brightening (intrinsic, Be-star-like)", "symmetric 0.33-mag bump over ~1 year, redder when brighter at 7 sigma (k 0.60 +- 0.04; dcol +0.11 +- 0.014) with no neighbour within 2\"; a lens would need an unresolved blend much bluer than the source"),
    "4069070918399108992": (X, 0.08, "young-star or Be-star brightening", "SIMBAD YSO candidate (Y*?); redder when brighter (k 0.48 +- 0.11; dcol +0.19 +- 0.05); GSP-Phot Teff ~9200 K; cut by the window start"),
}
V["4067152339419332992"] = (N, 0.85, "", "NEOWISE x7.3 (W1) / x8.2 (W2) on 2015-03-19, against x7.1 that the Gaia-only lens fit predicts for that moment; "
                            "Gaia G x4.4 at its brightest transit six days later, single in 2014-2017; ZTF 2018-2025 quiet; a KMTNet field "
                            "(22 KMT events within 15' in 2016-17) but the event was in 2015, before KMTNet's full survey, and OGLE EWS reports only 2 events within 15'")


def main():
    lc = pd.read_csv(os.path.join(DATA, "lc_metrics.csv"), dtype={"source_id": str}).set_index("source_id")
    assert set(V) == set(lc.index), set(lc.index) ^ set(V)
    rows = []
    for sid, (verdict, p, what, note) in V.items():
        m = lc.loc[sid]
        fj = json.load(open(os.path.join(DATA, "fits", f"{sid}.json")))
        lab = "parallax" if fj["fit"]["parallax"]["bic"] < fj["fit"]["static"]["bic"] else "static"
        t0 = fj["fit"][lab]["t0"]
        g = epoch(sid)[0]
        g = g[g.band == "G"]
        tfirst, tlast = float(g.t_mjd.min()), float(g.t_mjd.max())
        st = fj["fit"]["static"]
        # calibration (s13, 27 catalogued lenses): the fitted t0 is within 17 d of the survey's for 80%; static tE is
        # 0.59-1.43 x the survey's (16-84%, median 0.80). A fit t0 > 60 d from the brightest transit falls back to static.
        if np.isfinite(m.t_peak) and abs(t0 - m.t_peak) > 60:
            lab, t0 = "static", st["t0"]
        if t0 < tfirst:
            t0s = f"before {mjd2date(tfirst)} (declining at Gaia's first transits; fit t0 {mjd2date(t0)})"
        elif t0 > tlast:
            t0s = f"after {mjd2date(tlast)} (rising at DR3's end)"
        else:
            t0s = f"{mjd2date(t0)} +- 3 weeks ({lab} fit)"
        if sid == "2032454944878107008":
            ter = "binary lens; not a point lens"
        elif t0 < tfirst or t0 > tlast:
            ter = f"unconstrained (event cut by the DR3 window; static fit {st['tE']:.0f} d)"
        else:
            ter = f"{st['tE'] / 1.43:.0f}-{st['tE'] / 0.59:.0f} d (static fit {st['tE']:.0f} d; 68% calibrated)"
        amp = f"{m.A_obs_G:.2f}" if np.isfinite(m.A_obs_G) else "<1.3"
        if not np.isfinite(m.get("k_bp_rp", np.nan)):
            ach = "untested (no BP/RP at the bright transits)"
        elif m.base_BP > 20.5:
            ach = "untested (BP baseline fainter than 20.5)"
        elif abs(m.dcol_mean) <= 2.5 * m.dcol_err and abs(m.k_bp_rp - 1) <= 2.5 * m.k_err:
            ach = f"yes (k {m.k_bp_rp:.2f} +- {m.k_err:.2f})"
        elif m.dcol_mean > 0:
            ach = f"no: redder when brighter (k {m.k_bp_rp:.2f} +- {m.k_err:.2f}, dcol {m.dcol_mean:+.2f} +- {m.dcol_err:.2f})"
        else:
            ach = f"no: bluer when brighter (k {m.k_bp_rp:.2f} +- {m.k_err:.2f}, dcol {m.dcol_mean:+.2f} +- {m.dcol_err:.2f})"
        rows.append(dict(source_id=sid, verdict=verdict, p_lens=p, known_as=what if verdict in (K, C) else "",
                         what_instead=what if verdict == X else "", t0_robust=t0s, tE_range=ter, peak_amp=amp,
                         achromatic=ach, note=note))
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(WORK, "verdicts.csv"), index=False)
    print(out.verdict.value_counts().to_string())
    print(out[out.verdict == N].sort_values("p_lens", ascending=False)[["source_id", "p_lens", "t0_robust", "tE_range", "peak_amp",
                                                                          "achromatic"]].to_string())


if __name__ == "__main__":
    main()
