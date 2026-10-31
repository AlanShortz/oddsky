"""Shared loaders for the H-0009 ATLAS referee pass (ten strong events). Referee's own code; does not import the investigators'
scripts. Adapted from hunts/H-0008/reviews/claude-referee-atlas10b-2026-10-31/lib.py (rechecked).
Run from the repo root:  uv run python -I hunts/H-0009/reviews/claude-referee-atlas-2026-10-31/rN_*.py
"""
import os

import numpy as np
import pandas as pd

from oddsky.data import atlas

HERE = os.path.dirname(os.path.abspath(__file__))
H9 = os.path.abspath(os.path.join(HERE, "..", ".."))
W9 = os.path.join(H9, "work")
ATL = os.path.join(W9, "atlas")
DATA = os.path.join(HERE, "data")
FRAMES = os.path.join(DATA, "frames")
LC = os.path.expanduser("~/oddsky-runs/h0009/lightcurves")
SOUTH = ("03a", "04a")  # Chile / South Africa: local night straddles 0h UT
KEYS = ("J174401", "J180402", "J025145", "J185035", "J182621", "J184240", "J064439", "J172057", "J170153", "J173349")


def strong():
    s = pd.read_csv(os.path.join(W9, "sky4_strong.csv"), dtype={"g_source_id": str})
    s["allwise_cntr"] = s.allwise_cntr.astype("int64")
    return s


def targets():
    q = pd.read_csv(os.path.join(ATL, "queue.csv"))
    s = strong()
    out = {}
    for _, r in q.iterrows():
        k = r.designation.split(".")[0]
        row = s[s.designation == r.designation].iloc[0]
        out[k] = dict(name=r.designation, ra=float(row.ra), dec=float(row.dec), tvis=float(r.t_neowise),
                      t_first=float(row.t_first), t_last=float(row.t_last), t_prev=float(row.t_prev), t_next=float(row.t_next),
                      nblock=int(row.nblock), pixel=int(row.pixel), cntr=int(row.allwise_cntr), gaia=str(row.g_source_id),
                      gra=float(row.g_ra), gdec=float(row.g_dec), G=float(row.g_phot_g_mean_mag), bprp=float(row.g_bp_rp),
                      gsep=float(row.g_sep), l=float(row.l), b=float(row.b), dw1=float(row.dw1), dw2=float(row.dw2),
                      w1=float(row.w1mpro_allwise), w2=float(row.w2mpro_allwise), w3=float(row.w3mpro_allwise),
                      w4=float(row.w4mpro_allwise), J=float(row.j_m_2mass), K=float(row.k_m_2mass), w1med=float(row.w1_med),
                      row=row)
    return out


def atlas_raw(k):
    r = atlas.parse(open(os.path.join(ATL, f"atlas_{k}.txt")).read())
    r = r[r.F.isin(["c", "o"])].copy()
    r["cam"] = r.obs.str[:3]
    r["night"] = np.where(r.cam.isin(SOUTH), np.floor(r.mjd - 0.5), np.floor(r.mjd)).astype(int)
    r["year"] = 2000 + (r.mjd - 51544.5) / 365.25
    return r


def clean(r, m5min=17.5, chi_mode="rel", maj_max=None):
    """err==0, dujy>0, mag5sig>m5min. chi_mode 'rel': chi/N < max(10, 4 x unit/band median x max(1, |flux|/median flux))
    (chi/N grows with flux, so a fixed cut removes peaks); 'abs': chi/N<10; 'none'."""
    r = r[(r.err == 0) & (r.dujy > 0) & (r.mag5sig > m5min) & (r.ujy.abs() < 1e7)].copy()
    if maj_max is not None:
        r = r[r.maj < maj_max]
    if chi_mode == "abs":
        r = r[r.chi_n < 10]
    elif chi_mode == "rel":
        keep = np.ones(len(r), bool)
        for _, d in r.groupby(["F", "cam"]):
            fmed = max(np.median(np.abs(d.ujy)), 3 * np.median(d.dujy))
            lim = 4 * np.median(d.chi_n) * np.maximum(np.abs(d.ujy) / fmed, 1.0)
            keep[r.index.get_indexer(d.index)] = d.chi_n.values < np.maximum(lim, 10)
        r = r[keep]
    return r


def nightly(r, clip=4.0, nmin=1):
    """Per (band, unit, night): clip > clip robust sigma from the night median (>=3 frames), weighted mean;
    error = max(formal, std/sqrt(n))."""
    rows = []
    for (F, cam, night), d in r.groupby(["F", "cam", "night"]):
        f, e, t = d.ujy.values, d.dujy.values, d.mjd.values
        if len(f) >= 3:
            med = np.median(f)
            s = np.maximum(1.4826 * np.median(np.abs(f - med)), np.median(e))
            ok = np.abs(f - med) < clip * s
            f, e, t = f[ok], e[ok], t[ok]
        if len(f) < nmin:
            continue
        w = 1 / e**2
        m = np.sum(w * f) / np.sum(w)
        fe = 1 / np.sqrt(np.sum(w))
        if len(f) > 1:
            fe = max(fe, np.std(f, ddof=1) / np.sqrt(len(f)))
        rows.append((F, cam, night, float(np.mean(t)), m, fe, len(f), len(d), float(d.maj.median()), float(d["min"].median()),
                     float(d.mag5sig.median()), float(d.chi_n.median()), float(d.sky.median()), float(d.apfit.median())))
    return pd.DataFrame(rows, columns=["F", "cam", "night", "t", "ujy", "ujy_err", "n", "nraw", "maj", "mnr", "m5", "chi",
                                       "sky", "apfit"])


def neowise(k, T, raw=False):
    lc = pd.read_parquet(f"{LC}/pixel={T['pixel']}.parquet")
    lc = lc[lc.allwise_cntr.astype("int64") == np.int64(T["cntr"])].sort_values("t")
    if raw:
        return lc
    out = []
    for b in ("w1", "w2"):
        fl = 10 ** (-0.4 * lc[b].values)
        out.append(pd.DataFrame({"t": lc.t.values, "fl": fl, "fl_err": fl * lc[f"{b}_err"].values / 1.0857,
                                 "band": b.upper()}))
    return pd.concat(out, ignore_index=True)


def to_excess(t, fl, fe, label, base, floor="mad"):
    """Flux minus baseline median, with the excess robust baseline scatter added in quadrature."""
    t, fl, fe = map(np.asarray, (t, fl, fe))
    med = np.median(fl[base])
    d = fl - med
    e = fe.copy()
    if floor == "mad":
        rob = 1.4826 * np.median(np.abs(d[base] - np.median(d[base])))
        extra = np.sqrt(max(rob**2 - np.median(e[base]) ** 2, 0))
        e = np.hypot(e, extra)
    return pd.DataFrame({"t": t, "d": d, "e": e, "g": label, "base": med})


def frames(cntr):
    """NEOWISE single exposures within 6" (r0 download)."""
    p = os.path.join(FRAMES, f"{cntr}.csv")
    if not os.path.exists(p):
        return None
    d = pd.read_csv(p, dtype={"cc_flags": str, "ph_qual": str, "moon_masked": str, "source_id": str, "scan_id": str,
                              "allwise_cntr": str})
    # 19-digit ids: never through float64 (the sky1 merge bug)
    d["allwise_cntr"] = pd.array([int(x) if isinstance(x, str) and x.strip() not in ("", "nan") else pd.NA
                                  for x in d.allwise_cntr], dtype="Int64")
    d["cc_flags"] = d.cc_flags.fillna("0000").str.zfill(4)
    return d


def mjd2date(m):
    from astropy.time import Time
    return Time(m, format="mjd").iso[:10]


def ujy2ab(f):
    return 23.9 - 2.5 * np.log10(f)
