"""r1: re-reduction of the ten ATLAS forced-photometry files (reduced images).
Cuts: c/o, err==0, dujy>0, mag5sig>17.5, flux-scaled chi/N cut (lib.clean). Nightly per-unit/band weighted means with a 4-sigma
clip (southern units binned by local night). Baseline per unit/band: nights more than 400 d from every visit of the NEOWISE block.
Error floor: the unit's excess robust baseline scatter, added in quadrature.
For each star: baselines (positive?), PSF-width slope, coverage of the NEOWISE peak visit (+-10 d, +-30 d) and of every block visit,
the pooled excess there (weighted over units) and as a ratio to the baseline, the largest 20-d-binned excursion elsewhere, and the
nights within +-60 d of the peak visit. Writes data/r1_nightly_<k>.csv and data/r1_summary.json."""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, KEYS, atlas_raw, clean, mjd2date, neowise, nightly, targets, ujy2ab  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 500)
T = targets()
summ = {}


def pooled(ev):
    if len(ev) == 0:
        return None
    w = 1 / ev.e2**2
    m = float(np.sum(w * ev.exc) / np.sum(w))
    me = float(1 / np.sqrt(np.sum(w)))
    chi = float(np.sum(w * (ev.exc - m) ** 2) / max(len(ev) - 1, 1))
    me *= np.sqrt(max(chi, 1.0))
    # ratio: pooled excess over the weighted baseline of the contributing units
    bw = float(np.sum(w * ev.ubase) / np.sum(w))
    return dict(n=len(ev), exc=m, exc_err=me, base=bw, ratio=1 + m / bw if bw > 0 else np.nan,
                ratio_err=me / bw if bw > 0 else np.nan, chi2nu=chi)


for k in KEYS:
    t = T[k]
    tv = t["tvis"]
    lc = neowise(k, t, raw=True)
    vis = lc.t.values
    blk = vis[(vis >= t["t_first"] - 1) & (vis <= t["t_last"] + 1)]
    print("=" * 30, k, t["name"], f"G {t['G']:.2f} BP-RP {t['bprp']:.2f}  NEOWISE peak visit {tv:.2f} ({mjd2date(tv)}), "
          f"dW1 {t['dw1']:.2f}; block {len(blk)} visits: {[mjd2date(x) for x in blk]}")
    raw = atlas_raw(k)
    rc = clean(raw)
    print(f"raw c/o rows {len(raw)}; after cuts {len(rc)}; years {raw.year.min():.1f}-{raw.year.max():.1f}")
    nt = nightly(rc)
    nt["dvis"] = nt.t - tv
    dblk = np.min(np.abs(nt.t.values[:, None] - blk[None, :]), axis=1)
    nt["base"] = dblk > 400
    st = {}
    for (F, cam), d in nt.groupby(["F", "cam"]):
        b = d[d.base]
        if len(b) < 5:
            st[(F, cam)] = None
            continue
        med = float(np.median(b.ujy))
        rob = float(1.4826 * np.median(np.abs(b.ujy - med)))
        extra = float(np.sqrt(max(rob**2 - np.median(b.ujy_err) ** 2, 0)))
        st[(F, cam)] = dict(n=len(b), med=med, rob=rob, extra=extra, maj=float(b.maj.median()), snr=med / max(rob, 1))
    print("baselines (nights > 400 d from every block visit):")
    for (F, cam), v in sorted(st.items()):
        if v:
            print(f"  {F} {cam}: n {v['n']:4d} median {v['med']:8.1f} uJy ({ujy2ab(v['med']) if v['med'] > 0 else np.nan:.2f} AB) "
                  f"robust scatter {v['rob']:6.1f} (excess floor {v['extra']:5.1f}); median/scatter {v['snr']:5.1f}; PSF maj {v['maj']:.2f}")
    nt["ubase"] = [st[(F, c)]["med"] if st.get((F, c)) else np.nan for F, c in zip(nt.F, nt.cam)]
    nt["floor"] = [st[(F, c)]["extra"] if st.get((F, c)) else np.nan for F, c in zip(nt.F, nt.cam)]
    nt["exc"] = nt.ujy - nt.ubase
    nt["e2"] = np.hypot(nt.ujy_err, nt.floor)
    nt["ratio"] = nt.ujy / nt.ubase
    nt["sig"] = nt.exc / nt.e2
    # PSF slope on the baseline (per band, zero point per unit)
    slopes = {}
    for F, d in nt[nt.base & nt.ubase.notna()].groupby("F"):
        y = (d.ujy - d.ubase).values
        x = d.maj.values - d.maj.median()
        keep = np.ones(len(y), bool)
        for _ in range(3):
            A = np.vstack([np.ones(keep.sum()), x[keep]]).T
            p, *_ = np.linalg.lstsq(A, y[keep], rcond=None)
            res = y - (p[0] + p[1] * x)
            s = 1.4826 * np.median(np.abs(res[keep]))
            keep = np.abs(res) < 4 * s
        bm = np.median(d.ubase)
        slopes[F] = (float(p[1]), float(d.maj.median()))
        print(f"  PSF slope {F}: {p[1]:+.1f} uJy/px ({p[1] / bm * 100 if bm > 0 else np.nan:+.1f}%/px of {bm:.0f}); maj range "
              f"{d.maj.quantile(0.05):.1f}-{d.maj.quantile(0.95):.1f}")
    out = {"tvis": tv, "block": [float(x) for x in blk], "psf_slopes": slopes}
    # PSF-corrected excess (slope fitted on the baseline nights; applied to every night)
    nt["exc_psf"] = nt.exc - [slopes.get(F, (0, 0))[0] * (m - slopes.get(F, (0, 0))[1]) for F, m in zip(nt.F, nt.maj)]
    ok = nt[nt.ubase.notna()]
    for F in ("o", "c"):
        for win in (10, 30):
            ev = ok[(np.abs(ok.dvis) <= win) & (ok.F == F)].copy()
            if len(ev) == 0:
                continue
            ev["exc"] = ev.exc_psf
            p = pooled(ev)
            out[f"{F}_{win}_psf"] = p
            print(f"  {F} +-{win:2d} d PSF-corrected: excess {p['exc']:+8.1f} +- {p['exc_err']:6.1f} -> ratio {p['ratio']:.3f} +- {p['ratio_err']:.3f}")
    for F in ("o", "c", "both"):
        dd = ok if F == "both" else ok[ok.F == F]
        for win in (10, 30):
            ev = dd[np.abs(dd.dvis) <= win]
            p = pooled(ev)
            out[f"{F}_{win}"] = p
            if p:
                print(f"  {F:4s} +-{win:2d} d of peak visit: {p['n']:2d} nights, excess {p['exc']:+8.1f} +- {p['exc_err']:6.1f} uJy, "
                      f"baseline {p['base']:7.1f} -> ratio {p['ratio']:.3f} +- {p['ratio_err']:.3f} (chi2nu {p['chi2nu']:.1f})")
            else:
                print(f"  {F:4s} +-{win:2d} d of peak visit: NO ATLAS NIGHT")
    for x in blk:
        for win in (10, 30):
            ev = ok[(np.abs(ok.t - x) <= win) & (ok.F == "o")]
            p = pooled(ev)
            print(f"    block visit {mjd2date(x)} o +-{win}: " + (f"{p['n']} nights, ratio {p['ratio']:.3f} +- {p['ratio_err']:.3f}"
                                                                   if p else "none"))
    # nearest nights
    o = ok.copy()
    o["adt"] = o.dvis.abs()
    nn = o.sort_values("adt").head(3)
    print("  nearest nights:", "; ".join(f"{r.F} {r.cam} {r.dvis:+.1f} d ratio {r.ratio:.2f}" for r in nn.itertuples()))
    out["nearest_dt"] = float(nn.dvis.iloc[0])
    # 20-d bins elsewhere (o, all units pooled through excess)
    oo = ok[(ok.F == "o")].copy()
    oo["bin"] = np.floor((oo.t - tv) / 20).astype(int)
    rows = []
    for bn, d in oo.groupby("bin"):
        p = pooled(d)
        rows.append((bn * 20 + 10, p["n"], p["ratio"], p["ratio_err"], p["exc"] / p["exc_err"]))
    bb = pd.DataFrame(rows, columns=["dt", "n", "ratio", "err", "sig"])
    far = bb[(bb.dt.abs() > 60) & (bb.n >= 2)]
    if len(far):
        j = far.sig.idxmax()
        print(f"  largest 20-d o bin away from the visit (|dt|>60 d, >=2 nights): dt {far.dt[j]:+.0f} d ({mjd2date(tv + far.dt[j])}) "
              f"ratio {far.ratio[j]:.3f} +- {far.err[j]:.3f} ({far.sig[j]:.1f} sigma); bins > 5 sigma: {int((far.sig > 5).sum())} of {len(far)}")
        out["max_elsewhere"] = dict(dt=float(far.dt[j]), ratio=float(far.ratio[j]), err=float(far.err[j]), sig=float(far.sig[j]),
                                    n5=int((far.sig > 5).sum()), nbins=len(far))
    near = bb[(bb.dt.abs() <= 200)]
    print("  20-d o bins within 200 d:", " ".join(f"{r.dt:+.0f}:{r.ratio:.2f}({r.sig:+.1f})" for r in near.itertuples()))
    ev = ok[np.abs(ok.dvis) <= 60].sort_values("t").copy()
    ev["date"] = [mjd2date(x) for x in ev.t]
    print("  nights within 60 d of the peak visit:")
    if len(ev):
        print(ev[["date", "dvis", "F", "cam", "n", "nraw", "ujy", "ujy_err", "ubase", "ratio", "sig", "maj", "m5", "chi"]].round(2)
              .to_string(index=False))
    out["baselines"] = {f"{F}_{c}": v for (F, c), v in st.items() if v}
    summ[k] = out
    nt.to_csv(os.path.join(DATA, f"r1_nightly_{k}.csv"), index=False)
json.dump(summ, open(os.path.join(DATA, "r1_summary.json"), "w"), indent=1, default=float)
