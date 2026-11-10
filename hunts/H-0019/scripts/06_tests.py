"""The preregistered tests T1-T5 from work/measure.csv, plus the per-galaxy table. Writes work/tests.json, work/galaxies.csv."""
import json, pathlib
import numpy as np, pandas as pd
from scipy import stats

HERE = pathlib.Path(__file__).resolve().parents[1]
d = pd.read_csv(HERE / "work/measure.csv")
ref = pd.read_csv(HERE / "work/reference.csv"); ref = ref[ref.dtip == 0].groupby("cloud")[["E02", "E03", "E05", "Eb03"]].mean()
kcols = [c for c in d if c.startswith(("n_", "k0"))]
for kind in ("long", "short"):
    for box in ("agb", "agb_bright", "rgb", "blue"):
        for pre in ("n", "k02", "k03", "k05"):
            c = f"{pre}_{kind}_{box}"
            d[c] = d[c].fillna(0).astype(int) if c in d else 0
d["BMag"] = pd.to_numeric(d.BMag, errors="coerce")
g = d[(d.n_long_agb >= 50) & (d.n_long_rgb >= 50)].copy()


def E(k1, n1, k2, n2):
    f1, f2 = k1 / n1, k2 / n2
    return f1 - f2, float(np.sqrt(f1 * (1 - f1) / n1 + f2 * (1 - f2) / n2))


for x in ("02", "03", "05"):
    ev = [E(r[f"k{x}_long_agb"], r["n_long_agb"], r[f"k{x}_long_rgb"], r["n_long_rgb"]) for r in g.to_dict("records")]
    g[f"E{x}"], g[f"eE{x}"] = [a for a, _ in ev], [b for _, b in ev]
g = g.sort_values("BMag")
cols = ["name", "dist", "BMag", "colour", "tip", "tip_sig", "medlag_long", "n_long_agb", "k03_long_agb", "n_long_rgb", "k03_long_rgb",
        "n_long_blue", "k03_long_blue", "n_short_agb", "k03_short_agb", "sd_long_rgb", "E03", "eE03", "E02", "eE02"]
g[cols].to_csv(HERE / "work/galaxies.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
print(g[cols].round(4).to_string(index=False))


def pooled(s, x="03", kind="long"):
    return E(s[f"k{x}_{kind}_agb"].sum(), s[f"n_{kind}_agb"].sum(), s[f"k{x}_{kind}_rgb"].sum(), s[f"n_{kind}_rgb"].sum())


out = {"n_galaxies": len(g), "reference": ref.round(4).to_dict()}
e, se = pooled(g); out["T1"] = dict(E03=e, se=se, sigma=e / se, passed=bool(e / se >= 5))
sh = d[d.n_short_agb > 0]
fs = sh.k03_short_agb.sum() / max(sh.n_short_agb.sum(), 1); fb = g.k03_long_blue.sum() / max(g.n_long_blue.sum(), 1)
out["T2"] = dict(f03_short_agb=fs, n_short_agb=int(sh.n_short_agb.sum()), f03_long_blue=fb, n_long_blue=int(g.n_long_blue.sum()),
                 passed=bool(fs < 0.005 and fb < 0.015))
sh2 = d[(d.n_short_agb > 0) & (d.n_short_rgb > 0)]
es, ses = pooled(sh2, kind="short"); out["T3"] = dict(E03_short=es, se=ses, passed=bool(abs(es) < 2 * ses) if ses > 0 else bool(es == 0))
out["T4"] = dict(E03=e, se=se, window=[0.007, 0.042], passed=bool(0.007 <= e <= 0.042))
med = g.BMag.median(); lum, faint = g[g.BMag < med], g[g.BMag >= med]
el, sl = pooled(lum); ef, sf = pooled(faint); z = (el - ef) / np.hypot(sl, sf)
rho, p = stats.spearmanr(-g.BMag, g.E03)
out["T5"] = dict(median_MB=med, E03_luminous=el, se_luminous=sl, n_lum=len(lum), E03_faint=ef, se_faint=sf, n_faint=len(faint), z=z,
                 p_one_sided=float(stats.norm.sf(z)), spearman_rho_vs_luminosity=rho, spearman_p=p, passed=bool(stats.norm.sf(z) < 0.01))
for x in ("02", "05"):
    a, b = pooled(g, x); out[f"pooled_E{x}"] = dict(E=a, se=b)
a = E(g.k03_long_agb_bright.sum(), g.n_long_agb_bright.sum(), g.k03_long_rgb.sum(), g.n_long_rgb.sum()); out["pooled_Eb03"] = dict(E=a[0], se=a[1])
(HERE / "work/tests.json").write_text(json.dumps(out, indent=1, default=float))
print(json.dumps(out, indent=1, default=lambda v: round(float(v), 5)))
