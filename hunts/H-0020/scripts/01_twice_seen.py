"""Twice-seen on real Hubble fields.

Part A, shallow against deep: ANGST DOLPHOT "good star" catalogues of the same sky from a short and a long visit. The
deep one is the truth. Output: the short visit's completeness, offset and scatter in F814W, its half-recovery magnitude,
and the short catalogue's own median signal-to-noise there (DOLPHOT's good-star cut is S/N >= 4, so half-recovery should
fall where the short visit's S/N is a little above 4: a physical check that needs no artificial stars).

Part B, apertures against PSF fitting: the Hubble Source Catalog (summary table, F814W) against ANGST DOLPHOT as truth,
down to 1 mag below the red-giant tip (the catalogue was only fetched to 1.3 below, hunts/H-0019).

Writes work/shallow_deep.csv, work/hsc_quality.csv and the per-field tables work/tables/*.csv.
"""
import pathlib
import numpy as np, pandas as pd
from oddsky.analysis import twiceseen

RUN = pathlib.Path.home() / "oddsky-runs/h0019"; HERE = pathlib.Path(__file__).resolve().parents[1]
(HERE / "work/tables").mkdir(parents=True, exist_ok=True)
A = [  # galaxy, short visit (test), exposure s, long visit (truth), exposure s  [F814W exposure times from the HSC image list]
    ("Garland", "10915-ngc3077-wide1_f606w-f814w", 1622, "9381-ngc3077-phoenix_f555w-f814w", 19200),
    ("KKH 37", "9771-kkh37_f606w-f814w", 900, "10915-kkh37_f475w-f814w", 2541),
    ("NGC 4163", "9771-ngc4163_f606w-f814w", 900, "10915-ngc4163_f606w-f814w", 2250),
    ("M81 outer", "10584-m81-field-2_f606w-f814w", 1580, "10915-m81-deep_f606w-f814w", 29953),
    ("IC 2574", "10605-ic-2574-1-copy_f555w-f814w", 4784, "9755-ic2574-sgs_f555w-f814w", 6400),
]
B = [("NGC0300", ["10915-ngc0300-wide%d_f606w-f814w" % i for i in (1, 2, 3)]), ("GARLAND", ["9381-ngc3077-phoenix_f555w-f814w"]),
     ("NGC4163", ["10915-ngc4163_f606w-f814w"]), ("KKH37", ["10915-kkh37_f475w-f814w"]), ("IC2574", ["9755-ic2574-sgs_f555w-f814w"])]


def angst(tag):
    f = RUN / f"angst/{tag}_full.parquet"           # H-0019 cached these catalogues cut at F814W < 27; here the full depth is needed
    if not f.exists():
        import io, httpx
        from astropy.io import fits
        r = httpx.get(f"https://archive.stsci.edu/hlsps/angst/acs/hlsp_angst_hst_acs-wfc_{tag}_v1_gst.fits", timeout=900, follow_redirects=True); r.raise_for_status()
        t = fits.open(io.BytesIO(r.content))[1].data
        pd.DataFrame({k.lower(): np.asarray(t[k]).astype("f8") for k in ("RA", "DEC", "MAG1_ACS", "MAG2_ACS", "MAG2_ERR", "CROWD2", "SHARP2", "SNR2")}).to_parquet(f)
    d = pd.read_parquet(f)
    return d.rename(columns={"mag2_acs": "mag"})[["ra", "dec", "mag", "snr2", "crowd2"]].assign(snr=lambda x: x.snr2)


rows = []
for gal, short, t_s, deep, t_d in A:
    test, truth = angst(short), angst(deep)
    q = twiceseen.quality(truth, test)
    t = q["table"]; t.to_csv(HERE / f"work/tables/shallow_deep_{gal.replace(' ', '_')}.csv", index=False)
    lim = {c: twiceseen.limit(t, 0.5, c) for c in ("all", "isolated", "crowded")}
    m50 = lim["all"]["mag"]
    # not circular: the S/N the short visit should have at m50, from the long visit's S/N of the same stars scaled by exposure
    near = truth[(truth.mag > m50 - 0.15) & (truth.mag < m50 + 0.15)].assign(snr2=lambda x: x.snr2 * np.sqrt(t_s / t_d)) if m50 else truth.iloc[:0]
    truth_snr = float(truth[(truth.mag > m50 - 0.15) & (truth.mag < m50 + 0.15)].snr2.median()) if m50 else None
    v = t[(t.crowding == "all") & t.valid]
    bright = v[v.mag < v.mag.min() + 1.5]
    top = (t.mag < (m50 or t.mag.max()) - 1.5)             # well above the limit: what is lost here is not lost to depth
    iso = t[(t.crowding == "isolated") & top]; crd = t[(t.crowding == "crowded") & top]
    rows.append(dict(field=gal, short=short.split("_")[0], t_short=t_s, deep=deep.split("_")[0], t_deep=t_d, n_truth=q["n_truth_common"], n_matched=q["n_matched"],
                     tie_rms_mas=round(q["tie_rms_arcsec"] * 1000, 1), horizon=round(q["horizon"], 2), m50=round(m50, 2) if m50 else None, m50_valid=lim["all"]["valid"],
                     m50_isolated=lim["isolated"]["mag"] and round(lim["isolated"]["mag"], 2), m50_crowded=lim["crowded"]["mag"] and round(lim["crowded"]["mag"], 2),
                     snr_at_m50=round(float(near.snr2.median()), 1) if len(near) else None, truth_snr_at_m50=round(truth_snr, 1) if truth_snr else None, m90=(lambda x: x["mag"] and round(x["mag"], 2))(twiceseen.limit(t, 0.9)),
                     bright_completeness=round(float(np.average(bright.completeness, weights=bright.n)), 3), bright_scatter=round(float(bright.scatter.median()), 3),
                     valid_isolated=round(float(np.average(iso.completeness, weights=iso.n)), 3) if len(iso) else None,
                     valid_crowded=round(float(np.average(crd.completeness, weights=crd.n)), 3) if len(crd) else None,
                     zero_point=round(q["zero_point"], 3)))
    print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv(HERE / "work/shallow_deep.csv", index=False)

meas = pd.read_csv(HERE.parent / "H-0019/work/measure.csv").set_index("name")
rows = []
for key, tags in B:
    tip_ab = float(meas.tip[key.replace("_", " ")] if key.replace("_", " ") in meas.index else meas.tip[key]); tip_v = tip_ab - 0.68
    s = pd.read_parquet(RUN / f"hsc/{key}_sum.parquet")
    s = s[s.A_F814W.notna()]
    hsc_all = pd.DataFrame({"ra": s.MatchRA.values, "dec": s.MatchDec.values, "mag": s.A_F814W.values})
    clean = s.CI.between(0.85, 1.30).values
    for tag in tags:
        truth = angst(tag)                                                                     # full depth: neighbours are counted from all of it
        for label, test in (("all sources", hsc_all), ("point-like (CI 0.85-1.30)", hsc_all[clean].reset_index(drop=True))):
            try:
                q = twiceseen.quality(truth, test, radius=0.10, footprint="cells", mag_max=tip_v + 1.0)   # the catalogue fetch stops 1.3 mag below the tip
            except ValueError:
                continue
            t = q["table"]; t["valid"] = True                                                # truth is 3+ mag deeper than this range
            if q["n_truth_common"] < 300:
                continue
            t.to_csv(HERE / f"work/tables/hsc_{key}_{tag.split('_')[0]}_{label.split()[0]}.csv", index=False)
            for cls in ("all", "isolated", "crowded"):
                for name, lo, hi in (("above tip", -2.0, 0.0), ("0-1 below tip", 0.0, 1.0)):
                    g = t[(t.crowding == cls) & (t.mag - tip_v >= lo) & (t.mag - tip_v < hi)]
                    if g.n.sum() < 50:
                        continue
                    w = g.n
                    rows.append(dict(galaxy=key, truth=tag.split("_")[0], hsc=label, crowding=cls, range=name, n=int(w.sum()),
                                     completeness=round(float(np.average(g.completeness, weights=w)), 3), offset=round(float(np.average(g.offset.fillna(0), weights=w)), 3),
                                     scatter=round(float(np.average(g.scatter.fillna(0), weights=w)), 3), gross=round(float(np.average(g.gross.fillna(0), weights=w)), 4),
                                     displaced=round(float(np.average(g.displaced, weights=w)), 3),
                                     zero_point=round(q["zero_point"], 3), tie_rms_mas=round(q["tie_rms_arcsec"] * 1000, 1)))
df = pd.DataFrame(rows); df.to_csv(HERE / "work/hsc_quality.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
print(df[(df.hsc == "all sources")].to_string(index=False))
