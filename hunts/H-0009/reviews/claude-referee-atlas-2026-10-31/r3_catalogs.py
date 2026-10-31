"""r3: catalogue context for the ten stars (VizieR mirror vizier.idia.ac.za).
 - Gaia DR3 within 15": G, RP, BP-RP, parallax, RUWE, VarFlag; Gaussian-beam shares of the Gaia star in the ATLAS forced flux
   (FWHM ~4.5") and in the WISE beam (6.1", RP as the proxy); neighbours within 8".
 - 2MASS PSC within 15": Ks share of the 2MASS source nearest the AllWISE position in the WISE beam (the better W1 proxy), and
   whether that 2MASS source is the Gaia star (separation; G-Ks against BP-RP).
 - AllWISE within 60": bright W1 neighbours (halo/spike sources), ccf/ex/nb of the target.
 - VSX (B/vsx) and SIMBAD-class hints (via VizieR is not possible: SIMBAD is queried in r9).
Writes data/r3_shares.json."""
import io
import json
import os
import sys

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, KEYS, targets  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
UA = {"User-Agent": "Mozilla/5.0 (oddsky referee)"}
T = targets()


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
        if v.notna().sum() >= max(1, 0.5 * df[c].notna().sum()) and c not in ("Source", "2MASS", "AllWISE", "ccf", "qph", "Qflg"):
            df[c] = v
        else:
            df[c] = df[c].str.strip()
    return df


def gshare(sep_from_target_star, mags, fwhm, tg):
    s = fwhm / 2.355
    w = 10 ** (-0.4 * mags) * np.exp(-sep_from_target_star**2 / (4 * s**2))  # overlap of two Gaussians (PSF-fit weight)
    return float(w[tg].sum() / w.sum())


out = {}
for k in KEYS:
    t = T[k]
    print("=" * 30, k, t["name"], f"Gaia DR3 {t['gaia']} (sep {t['gsep']:.2f}\")  l {t['l']:.2f} b {t['b']:+.2f}")
    print(f"  J {t['J']:.2f} K {t['K']:.2f} W1 {t['w1']:.2f} W2 {t['w2']:.2f} W3 {t['w3']:.2f} W4 {t['w4']:.2f}; J-K {t['J'] - t['K']:.2f} "
          f"K-W1 {t['K'] - t['w1']:.2f} W1-W2 {t['w1'] - t['w2']:+.2f} K-W3 {t['K'] - t['w3']:.2f} W1-W4 {t['w1'] - t['w4']:.2f}")
    g = viz("I/355/gaiadr3", t["ra"], t["dec"], 20, "Source,RA_ICRS,DE_ICRS,Gmag,BPmag,RPmag,BP-RP,Plx,e_Plx,RUWE,VarFlag,IPDfmp,NSS")
    tg = (g.Source.astype(str) == t["gaia"]).values
    if not tg.any():
        print("  target Gaia source not found within 20\"")
        continue
    # separations from the Gaia target star (not the AllWISE position)
    ra0, de0 = float(g.RA_ICRS[tg].iloc[0]), float(g.DE_ICRS[tg].iloc[0])
    g["sepT"] = np.hypot((g.RA_ICRS - ra0) * np.cos(np.radians(de0)), g.DE_ICRS - de0) * 3600
    om = np.where(g.RPmag.notna(), (g.Gmag + g.RPmag) / 2, g.Gmag - 0.5)
    rp = g.RPmag.fillna(g.Gmag - 1).values
    sA = gshare(g.sepT.values, om, 4.5, tg)
    sW_rp = gshare(g.sepT.values, rp, 6.1, tg)
    near = g[(g.sepT < 8) & ~tg]
    print(f"  Gaia within 8\" of the star: {len(near)} neighbours; G of the target {float(g.Gmag[tg].iloc[0]):.2f}")
    print(g[g.sepT < 10][["Source", "_r", "sepT", "Gmag", "RPmag", "BP-RP", "Plx", "e_Plx", "RUWE", "VarFlag", "IPDfmp"]].round(3)
          .to_string(index=False))
    m2 = viz("II/246/out", t["ra"], t["dec"], 20, "2MASS,RAJ2000,DEJ2000,Jmag,Hmag,Kmag,Qflg,Cflg")
    k_share, sep_2m_gaia, gk = np.nan, np.nan, np.nan
    if not m2.empty:
        m2["sepT"] = np.hypot((m2.RAJ2000 - ra0) * np.cos(np.radians(de0)), m2.DEJ2000 - de0) * 3600
        j = int(np.argmin(m2["_r"].values))  # 2MASS source nearest the AllWISE position
        tg2 = np.zeros(len(m2), bool)
        tg2[j] = True
        m2["sepJ"] = np.hypot((m2.RAJ2000 - m2.RAJ2000.iloc[j]) * np.cos(np.radians(de0)), m2.DEJ2000 - m2.DEJ2000.iloc[j]) * 3600
        k_share = gshare(m2.sepJ.values, m2.Kmag.fillna(m2.Kmag.max() + 1).values, 6.1, tg2)
        sep_2m_gaia = float(m2.sepT.iloc[j])
        gk = float(g.Gmag[tg].iloc[0] - m2.Kmag.iloc[j])
        print(f"  2MASS within 10\" of the AllWISE position:")
        print(m2[m2["_r"] < 10][["2MASS", "_r", "sepT", "Jmag", "Hmag", "Kmag", "Qflg", "Cflg"]].round(2).to_string(index=False))
        print(f"  nearest 2MASS to AllWISE: {m2['2MASS'].iloc[j]} at {m2['_r'].iloc[j]:.2f}\" from AllWISE, {sep_2m_gaia:.2f}\" from the Gaia "
              f"star; Ks share of the WISE beam {k_share:.3f}; G-Ks {gk:.2f} for BP-RP {t['bprp']:.2f}")
    aw = viz("II/328/allwise", t["ra"], t["dec"], 60, "AllWISE,W1mag,W2mag,W3mag,W4mag,ccf,ex,nb,na,qph")
    if not aw.empty:
        print("  AllWISE within 60\" (W1 < target + 1 or within 10\"):")
        tw1 = float(aw.W1mag.iloc[0])
        print(aw[(aw.W1mag < tw1 + 1) | (aw["_r"] < 10)][["AllWISE", "_r", "W1mag", "W2mag", "W3mag", "W4mag", "ccf", "ex", "nb", "qph"]]
              .round(2).to_string(index=False))
    v = viz("B/vsx/vsx", t["ra"], t["dec"], 60, "Name,Type,max,min,Period,_r")
    print("  VSX within 60\":", "none" if v.empty else v.to_dict("records"))
    # simple lens-on-the-Gaia-star expectation
    rW = 10 ** (-0.4 * t["dw1"])
    sW = k_share if np.isfinite(k_share) else sW_rp
    A = 1 + (rW - 1) / sW  # magnification of the Gaia star implied by the W1 ratio if the Gaia star carries share sW of W1
    rA = 1 + (A - 1) * sA
    print(f"  W1 ratio at the visit {rW:.2f}; Gaia-star share: ATLAS {sA:.3f}, WISE (RP proxy) {sW_rp:.3f}, WISE (2MASS Ks proxy) "
          f"{k_share:.3f}. A lens on the Gaia star would need A = {A:.2f} and give ATLAS x{rA:.2f} at the visit "
          f"(x{1 + (rW - 1) * sA:.2f} if the Gaia star supplies all of W1)")
    out[k] = dict(sA=sA, sW_rp=sW_rp, sW_k=k_share, n8=len(near), sep_2m_gaia=sep_2m_gaia, gk=gk, rW=rW, A_needed=A, rA_pred=rA)
json.dump(out, open(os.path.join(DATA, "r3_shares.json"), "w"), indent=1, default=float)
