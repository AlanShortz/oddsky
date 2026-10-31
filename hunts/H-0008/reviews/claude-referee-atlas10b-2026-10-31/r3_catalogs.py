"""r3: catalogue context (VizieR mirror vizier.idia.ac.za).
 - Gaia DR3 within 15": G, BP, RP, parallax, RUWE, VarFlag, IPD multi-peak, NSS; Gaussian-PSF share of the ATLAS forced flux
   (FWHM ~2.4 px = 4.5") and of the WISE beam (6.1"); expected ATLAS o of the target (o ~ (G+RP)/2) vs the measured baseline;
 - Gaia DR3 astrophysical parameters (I/355/paramp), variability (I/358: varisum, vclassre, vlpv);
 - DR3 G-flux scatter (e_FG*sqrt(N)/FG) vs stars within 3' and 0.5 mag;
 - 2MASS (II/246), AllWISE (II/328) photometry and quality flags; VSX (B/vsx/vsx) and ASAS-SN variables (II/366) within 60".
"""
import io
import os
import sys

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import targets  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
UA = {"User-Agent": "Mozilla/5.0 (oddsky referee)"}
T = targets()
BASE_O = {"J175634": 3300, "J174744": 12040}  # r1: ATLAS o baseline (zero point of the unit fits)
BASE_C = {"J175634": 869, "J174744": 3126}


def viz(cat, ra, dec, r, cols="**"):
    q = requests.get("https://vizier.idia.ac.za/viz-bin/asu-tsv",
                     params={"-source": cat, "-c": f"{ra} {dec}", "-c.rs": r, "-out": cols, "-out.add": "_r", "-sort": "_r",
                             "-out.max": 5000, "-c.u": "arcsec"}, headers=UA, timeout=240)
    lines = [ln for ln in q.text.splitlines() if ln and not ln.startswith("#")]
    if len(lines) < 3:
        return pd.DataFrame()
    df = pd.read_csv(io.StringIO("\n".join([lines[0]] + lines[3:])), sep="\t", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    for c in df.columns:
        v = pd.to_numeric(df[c].str.strip(), errors="coerce")
        if v.notna().sum() >= max(1, 0.5 * df[c].notna().sum()) and c not in ("Source", "DR3Name"):
            df[c] = v
        else:
            df[c] = df[c].str.strip()
    return df


for k, t in T.items():
    print("=" * 30, k, t["name"], f"Gaia DR3 {t['gaia']}  l {t['l']:.2f} b {t['b']:+.2f}")
    print(f"  sky3 row: J {t['J']:.2f} K {t['K']:.2f} W1 {t['w1']:.2f} W2 {t['w2']:.2f} W3 {t['w3']:.2f} W4 {t['w4']:.2f}; "
          f"J-K {t['J'] - t['K']:.2f} W1-W2 {t['w1'] - t['w2']:+.2f} W2-W3 {t['w2'] - t['w3']:+.2f} W3-W4 {t['w3'] - t['w4']:+.2f}")
    g = viz("I/355/gaiadr3", t["ra"], t["dec"], 15, "Source,RA_ICRS,DE_ICRS,Gmag,BPmag,RPmag,BP-RP,Plx,e_Plx,pmRA,pmDE,RUWE,"
            "VarFlag,IPDfmp,IPDgofha,NSS,o_Gmag,FG,e_FG,E(BP/RP),Teff,logg,Dist,AG")
    g["sep"] = g["_r"]
    sig = 2.4 * 1.86 / 2.355
    om = np.where(g.RPmag.notna(), (g.Gmag + g.RPmag) / 2, g.Gmag - 0.5)
    g["o_est"] = om
    g["w_atlas"] = 10 ** (-0.4 * om) * np.exp(-g.sep**2 / (4 * sig**2))
    sw = 6.1 / 2.355
    g["w_wise"] = 10 ** (-0.4 * g.RPmag.fillna(g.Gmag - 1)) * np.exp(-g.sep**2 / (4 * sw**2))
    tg = g.Source == t["gaia"]
    print(g[["Source", "sep", "Gmag", "BPmag", "RPmag", "BP-RP", "Plx", "e_Plx", "RUWE", "VarFlag", "IPDfmp", "IPDgofha", "NSS",
             "o_Gmag", "E(BP/RP)", "w_atlas"]].round(3).to_string(index=False))
    o_t = float(g.o_est[tg].iloc[0])
    fo = 10 ** (-0.4 * (o_t - 23.9))
    share = g.w_atlas[tg].sum() / g.w_atlas.sum()
    print(f"  expected ATLAS o of the Gaia star ~{o_t:.2f} AB = {fo:.0f} uJy; ATLAS baseline {BASE_O[k]} uJy -> ratio "
          f"{BASE_O[k] / fo:.2f}; Gaia-only share of the ATLAS forced flux {share:.3f}; of WISE beam (RP proxy) "
          f"{g.w_wise[tg].sum() / g.w_wise.sum():.3f}; sources within 2\" {int(((g.sep < 2) & ~tg).sum())}, within 4\" "
          f"{int(((g.sep < 4) & ~tg).sum())}")
    print(f"  ATLAS c-o (baseline, AB) {-2.5 * np.log10(BASE_C[k] / BASE_O[k]):.2f}")
    ap = viz("I/355/paramp", t["ra"], t["dec"], 3, "**")
    if not ap.empty:
        ap = ap[ap.Source.astype(str) == t["gaia"]]
        keep = [c for c in ap.columns if any(s in c for s in ("Teff", "logg", "[M/H]", "Dist", "AG", "ABP", "SpType", "EWHa",
                                                               "ClassELS", "Rad", "Lum", "Evol", "Mass", "Age", "PQSO",
                                                               "PSS", "PGal", "Pstar", "PWD", "PBin"))]
        print("  astrophysical parameters:", {c: ap[c].iloc[0] for c in keep if pd.notna(ap[c].iloc[0]) and ap[c].iloc[0] != ""})
    for cat in ("I/358/varisum", "I/358/vclassre", "I/358/vlpv"):
        v = viz(cat, t["ra"], t["dec"], 5)
        print(f"  {cat}: " + ("none within 5\"" if v.empty else v.drop(columns=[c for c in v.columns if c.startswith("_")]).to_dict("records").__str__()[:600]))
    # DR3 scatter vs neighbours
    G = float(g.Gmag[tg].iloc[0])
    c = viz("I/355/gaiadr3", t["ra"], t["dec"], 180, "Source,Gmag,FG,e_FG,o_Gmag,BP-RP")
    c = c[(c.Gmag > G - 0.5) & (c.Gmag < G + 0.5)]
    c["s"] = c.e_FG * np.sqrt(c.o_Gmag) / c.FG
    ts = float((g.e_FG * np.sqrt(g.o_Gmag) / g.FG)[tg].iloc[0])
    print(f"  DR3 G-flux scatter (2014.6-2017.4) target {ts:.4f} (N {int(g.o_Gmag[tg].iloc[0])}); {len(c)} stars within 3' and "
          f"0.5 mag: median {c.s.median():.4f}, 90th {c.s.quantile(0.9):.4f}, 99th {c.s.quantile(0.99):.4f}; percentile "
          f"{100 * (c.s < ts).mean():.1f}")
    m2 = viz("II/246/out", t["ra"], t["dec"], 5, "2MASS,Jmag,e_Jmag,Hmag,e_Hmag,Kmag,e_Kmag,Qflg,Rflg,Bflg,Cflg,Xflg")
    print("  2MASS within 5\":", m2.drop(columns=[]).round(3).to_dict("records"))
    aw = viz("II/328/allwise", t["ra"], t["dec"], 8, "AllWISE,W1mag,e_W1mag,W2mag,e_W2mag,W3mag,e_W3mag,W4mag,e_W4mag,ccf,ex,var,qph,nb,na,Jmag,Hmag,Kmag")
    print("  AllWISE within 8\":", aw.round(3).to_dict("records"))
    for cat, rr in (("B/vsx/vsx", 120), ("II/366/catalog", 120)):
        v = viz(cat, t["ra"], t["dec"], rr)
        print(f"  {cat} within {rr}\": " + ("none" if v.empty else "\n    " + v.drop(columns=[c for c in v.columns if c.startswith("_") and c != "_r"]).to_string(index=False).replace("\n", "\n    ")))
