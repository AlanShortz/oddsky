"""s7: blending and neighbours, for the colour test and to rule out a neighbour as the variable.
  * Gaia DR3 neighbours within 2" and 6" (s1), their G flux relative to the target, and the share of the BP/RP window flux
    (neighbours within 1.75", half the 3.5" window length) that belongs to the target in BP and in RP. If only the target is
    magnified, the BP and RP excess-flux ratios scale with those shares: k_lens = share_BP / share_RP (neighbours without
    BP/RP photometry are given the target's colour, i.e. they dilute both bands alike).
  * The corrected BP/RP flux excess C* and its significance (Riello et al. 2021), a direct flag of window contamination.
  * Every neighbour within 6" with DR3 epoch photometry (s2 --neighbours): does it brighten at the target's event?
Run from the repo root: uv run python -I hunts/H-0010/scripts/s7_neighbours.py
Writes hunts/H-0010/data/neighbours_summary.csv."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, EP, baseline, targets  # noqa: E402


def cstar(c, x, g):
    if not np.isfinite(x) or not np.isfinite(c):
        return np.nan, np.nan
    if x < 0.5:
        f = 1.154360 + 0.033772 * x + 0.032277 * x**2
    elif x < 4:
        f = 1.162004 + 0.011464 * x + 0.049255 * x**2 - 0.005879 * x**3
    else:
        f = 1.057572 + 0.140537 * x
    s = 0.0059898 + 8.817481e-12 * g**7.618399
    return c - f, (c - f) / s


def main():
    T = targets()
    lc = pd.read_csv(os.path.join(DATA, "lc_metrics.csv"), dtype={"source_id": str}).set_index("source_id")
    nb = pd.read_csv(os.path.join(DATA, "neighbours.csv"), dtype={"nb_source_id": str, "target": str})
    rows = []
    for r in T.itertuples():
        n = nb[nb.target == r.source_id]
        n2, n175 = n[n.sep < 2], n[n.sep < 1.75]
        fg = 10 ** (-0.4 * (n2.phot_g_mean_mag - r.phot_g_mean_mag))
        shares = {}
        for band, col in (("BP", "phot_bp_mean_mag"), ("RP", "phot_rp_mean_mag")):
            tm = getattr(r, col)
            nm = n175[col].where(np.isfinite(n175[col]), n175.phot_g_mean_mag + (tm - r.phot_g_mean_mag))
            ft = 10 ** (-0.4 * tm) if np.isfinite(tm) else np.nan
            shares[band] = ft / (ft + np.nansum(10 ** (-0.4 * nm)))
        cs, csig = cstar(r.phot_bp_rp_excess_factor, r.bp_rp, r.phot_g_mean_mag)
        rec = dict(source_id=r.source_id, n_nb_2as=len(n2), n_nb_6as=len(n), brightest_nb_2as_dG=(round(float(n2.phot_g_mean_mag.min() - r.phot_g_mean_mag), 2) if len(n2) else None),
                   nb_flux_2as_over_target_G=round(float(fg.sum()), 3), share_BP=round(float(shares["BP"]), 3),
                   share_RP=round(float(shares["RP"]), 3), k_lens_expected=round(float(shares["BP"] / shares["RP"]), 3),
                   cstar=round(float(cs), 3) if np.isfinite(cs) else None, cstar_sig=round(float(csig), 1) if np.isfinite(csig) else None)
        # neighbours with epoch photometry
        ev = lc.loc[r.source_id]
        tpk = ev.t_peak if np.isfinite(ev.t_peak) else ev.static_t0
        notes = []
        for x in n[n.has_epoch_photometry.astype(str).str.lower() == "true"].itertuples():
            p = os.path.join(EP, f"{x.nb_source_id}.csv")
            if not os.path.exists(p):
                notes.append(f"{x.nb_source_id}@{x.sep:.1f}\": no file")
                continue
            d = pd.read_csv(p)
            d = d[(d.band == "G") & (d.flag != "rejected_by_photometry") & np.isfinite(d.mag)]
            bl, sig, _ = baseline(d.t_mjd.values, d.mag.values, d.err.values)
            near = d[np.abs(d.t_mjd - tpk) < 30]
            dmin = float((near.mag - bl).min()) if len(near) else np.nan
            notes.append(f"{x.nb_source_id}@{x.sep:.1f}\" G{x.phot_g_mean_mag:.1f}: dG(+-30d) {dmin:+.2f} (sig {sig:.3f})")
        rec["nb_epoch"] = "; ".join(notes)
        rows.append(rec)
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(DATA, "neighbours_summary.csv"), index=False)
    print(out.to_string())


if __name__ == "__main__":
    main()
