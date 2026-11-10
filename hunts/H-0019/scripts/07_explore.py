"""Exploratory (not preregistered): noise-matched significance per star, clean-field subsets, lag dependence,
tip-placement sensitivity, and the list of individual large-change candidates. Reads work/pairs/*.parquet.

Writes work/explore.json and work/candidates.csv.
"""
import json, pathlib
import numpy as np, pandas as pd

HERE = pathlib.Path(__file__).resolve().parents[1]
meas = pd.read_csv(HERE / "work/measure.csv").set_index("name")
gal = pd.read_csv(HERE / "work/galaxies.csv")
out, cands, allp = {}, [], []


def local_sigma(p):
    """Robust scatter of the control stars (everything not in an AGB box) against magnitude, per image pair."""
    sig = np.full(len(p), np.nan)
    ctrl = ~p.box.isin(["agb", "agb_bright"]).values
    for _, idx in p.groupby(["kind", "img1", "img2"]).indices.items():
        q = p.iloc[idx]; c = ctrl[idx]
        if c.sum() < 30:
            continue
        o = np.argsort(q.rel.values[c]); r = q.rel.values[c][o]; a = np.abs(q.d.values[c][o])
        n = max(15, len(r) // 8)
        cen = [np.median(r[i:i + n]) for i in range(0, len(r) - n + 1, max(1, n // 2))]
        sd = [1.4826 * np.median(a[i:i + n]) for i in range(0, len(r) - n + 1, max(1, n // 2))]
        sig[idx] = np.maximum(np.interp(q.rel.values, cen, sd), 0.015)
    return sig


for name in gal.name:
    key = name.replace(" ", "_")
    p = pd.read_parquet(HERE / f"work/pairs/{key}.parquet")
    p["sig"] = local_sigma(p); p["z"] = p.d / p.sig; p["gal"] = name
    allp.append(p[p.kind == "long"])
    c = p[(p.kind == "long") & p.box.isin(["agb", "agb_bright"]) & (p.d.abs() > 0.5) & (p.z.abs() > 5)]
    cands.append(c)
A = pd.concat(allp, ignore_index=True)
C = pd.concat(cands, ignore_index=True)
C[["gal", "MatchID", "MatchRA", "MatchDec", "box", "rel", "mag1", "mag2", "d", "sig", "z", "lag", "mjd1", "col"]].round(5).to_csv(HERE / "work/candidates.csv", index=False)


def E(s, x=0.3, box="agb"):
    a, r = s[s.box == box], s[s.box == "rgb"]
    if len(a) < 20 or len(r) < 20:
        return None
    f1, f2 = (a.d.abs() > x).mean(), (r.d.abs() > x).mean()
    return dict(E=round(float(f1 - f2), 4), se=round(float(np.sqrt(f1 * (1 - f1) / len(a) + f2 * (1 - f2) / len(r))), 4), n_agb=len(a), n_rgb=len(r),
                f_agb=round(float(f1), 4), f_rgb=round(float(f2), 4))


def Ez(s, zmin=5, x=0.3, box="agb"):
    """Same, counting only changes that are also > zmin local sigma (noise-matched)."""
    a, r = s[s.box == box], s[s.box == "rgb"]
    f1 = ((a.d.abs() > x) & (a.z.abs() > zmin)).mean(); f2 = ((r.d.abs() > x) & (r.z.abs() > zmin)).mean()
    return dict(E=round(float(f1 - f2), 4), se=round(float(np.sqrt(f1 * (1 - f1) / len(a) + f2 * (1 - f2) / len(r))), 4), f_agb=round(float(f1), 4), f_rgb=round(float(f2), 4), n_agb=len(a))


sd = gal.set_index("name").sd_long_rgb
clean = [n for n in gal.name if sd[n] < 0.05]; noisy = [n for n in gal.name if sd[n] >= 0.05]
out["clean_galaxies"], out["noisy_galaxies"] = clean, noisy
out["E03_clean"], out["E03_noisy"] = E(A[A.gal.isin(clean)]), E(A[A.gal.isin(noisy)])
out["E02_clean"], out["E05_clean"] = E(A[A.gal.isin(clean)], 0.2), E(A[A.gal.isin(clean)], 0.5)
out["Eb03_clean"] = E(A[A.gal.isin(clean)], 0.3, "agb_bright")
out["E03_z5_all"], out["E03_z5_clean"], out["E03_z5_noisy"] = Ez(A), Ez(A[A.gal.isin(clean)]), Ez(A[A.gal.isin(noisy)])
out["per_galaxy_z5"] = {n: Ez(A[A.gal == n]) for n in gal.name}
out["by_lag"] = {f"{lo}-{hi}": E(A[(A.lag >= lo) & (A.lag < hi)]) for lo, hi in [(100, 300), (300, 1000), (1000, 2000), (2000, 5000)]}
out["by_lag_clean"] = {f"{lo}-{hi}": E(A[(A.lag >= lo) & (A.lag < hi) & A.gal.isin(clean)]) for lo, hi in [(100, 1000), (1000, 5000)]}
# tip sensitivity: shift the tip by +-0.1 mag and rebuild the two red boxes
for dt in (-0.1, 0.1):
    s = A[A.cls == "red"].copy(); rel = s.rel - dt
    s["box"] = np.select([(rel >= -1) & (rel < 0), (rel > 0) & (rel <= 0.5)], ["agb", "rgb"], "other")
    out[f"E03_tip{dt:+.1f}"] = E(s); out[f"E03_tip{dt:+.1f}_clean"] = E(s[s.gal.isin(clean)])
# redder colour cut: drop the bluest third of the red stars in each galaxy (helium-burning stars sit there)
s = A[A.cls == "red"].copy(); s = s[s.col > s.groupby("gal").col.transform(lambda v: v.quantile(0.33))]
out["E03_redder"] = E(s); out["E03_redder_clean"] = E(s[s.gal.isin(clean)])
out["n_candidates"] = int(len(C)); out["candidates_by_galaxy"] = C.gal.value_counts().to_dict()
out["candidates_dimmed_vs_brightened"] = [int((C.d > 0).sum()), int((C.d < 0).sum())]
(HERE / "work/explore.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
