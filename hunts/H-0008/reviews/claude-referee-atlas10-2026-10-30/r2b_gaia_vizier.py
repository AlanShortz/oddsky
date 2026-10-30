"""r2b: the Gaia DR3 part of r2 through VizieR (vizier.idia.ac.za; the ESA TAP took ~1 min per query today).
 - DR3 sources within 10" (I/355/gaiadr3): G, BP, RP, parallax, RUWE, variability flag, IPD multi-peak; share of the ATLAS
   forced flux (Gaussian overlap, FWHM 4.5") and expected ATLAS o flux of the target from G and RP (o ~ (G + RP)/2, AB);
 - astrophysical parameters (I/355/paramp);
 - DR3 G-flux scatter e_FG*sqrt(N)/FG vs stars within 3' and 0.5 mag (events inside 2014.6-2017.4 inflate it).
"""
import io
import os
import sys

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, targets  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 30)
UA = {"User-Agent": "Mozilla/5.0 (oddsky referee)"}
T = targets()
NEXT = {"J163539": 186, "J075219": 33, "J185846": 51, "J174440": 1260, "J182120": 880, "J173150": 4150, "J191120": 95}


def viz(cat, ra, dec, r, cols):
    q = requests.get("https://vizier.idia.ac.za/viz-bin/asu-tsv", params={"-source": cat, "-c": f"{ra} {dec}", "-c.rs": r,
                     "-out": cols, "-out.add": "_r", "-sort": "_r", "-out.max": 5000}, headers=UA, timeout=180)
    lines = [ln for ln in q.text.splitlines() if ln and not ln.startswith("#")]
    if len(lines) < 3:
        return pd.DataFrame()
    df = pd.read_csv(io.StringIO("\n".join([lines[0]] + lines[3:])), sep="\t", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    for c in df.columns:
        if c not in ("Source", "VarFlag"):
            df[c] = pd.to_numeric(df[c].str.strip(), errors="coerce")
    return df


cols = "Source,Gmag,BPmag,RPmag,BP-RP,Plx,e_Plx,RUWE,VarFlag,IPDfmp,FG,e_FG,o_Gmag,NSS"
for k, t in T.items():
    print("=" * 30, k, t["name"], f"target Gaia DR3 {t['gaia']}")
    g = viz("I/355/gaiadr3", t["ra"], t["dec"], 10, cols)
    if g.empty:
        print("  UNKNOWN (VizieR returned nothing)")
        continue
    g["Source"] = g.Source.str.strip()
    g["sep"] = g["_r"] * (60 if g["_r"].max() < 1 else 1)  # _r in arcmin or arcsec depending on server default
    sig = 2.4 * 1.86 / 2.355
    om = np.where(g.RPmag.notna(), (g.Gmag + g.RPmag) / 2, g.Gmag - 0.5)
    g["o_est"] = om
    g["w"] = 10 ** (-0.4 * om) * np.exp(-g.sep**2 / (4 * sig**2))
    tg = g.Source == t["gaia"]
    print(g[["Source", "sep", "Gmag", "BPmag", "RPmag", "BP-RP", "Plx", "e_Plx", "RUWE", "VarFlag", "IPDfmp", "NSS", "o_Gmag"]]
          .round(3).to_string(index=False))
    if tg.any():
        o_t = float(g.o_est[tg].iloc[0])
        print(f"  target: expected ATLAS o of the Gaia star ~{o_t:.2f} AB = {10 ** (-0.4 * (o_t - 23.9)):.0f} uJy; ATLAS reduced-image "
              f"baseline median ~{NEXT[k]} uJy (ratio {NEXT[k] / 10 ** (-0.4 * (o_t - 23.9)):.2f}); Gaia-only share of the forced "
              f"flux {g.w[tg].sum() / g.w.sum():.3f}; other sources within 3\": {int(((g.sep < 3) & ~tg).sum())}")
        ap = viz("I/355/paramp", t["ra"], t["dec"], 2, "Source,Teff,logg,[M/H],Dist,AG,SpType-ELS,EWHa,ClassELS,Rad,Lum-Flame")
        if not ap.empty:
            ap["Source"] = ap.Source.astype(str).str.strip()
            print("  astrophysical parameters:", ap[ap.Source == t["gaia"]].drop(columns=["_r"]).to_dict("records"))
        G = float(g.Gmag[tg].iloc[0])
        c = viz("I/355/gaiadr3", t["ra"], t["dec"], 180, "Source,Gmag,FG,e_FG,o_Gmag")
        c = c[(c.Gmag > G - 0.5) & (c.Gmag < G + 0.5)]
        c["s"] = c.e_FG * np.sqrt(c.o_Gmag) / c.FG
        ts = float((g.e_FG * np.sqrt(g.o_Gmag) / g.FG)[tg].iloc[0])
        print(f"  DR3 G-flux scatter target {ts:.4f} (N {int(g.o_Gmag[tg].iloc[0])}); {len(c)} stars within 3' and 0.5 mag: median "
              f"{c.s.median():.4f}, 90th {c.s.quantile(0.9):.4f}, 99th {c.s.quantile(0.99):.4f}; percentile {100 * (c.s < ts).mean():.1f}")
    else:
        print("  TARGET ID NOT FOUND")
