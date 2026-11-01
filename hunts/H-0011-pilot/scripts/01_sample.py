"""H-0011 pilot, step 1: the red-supergiant sample.

CDS (VizieR, cdsarc) and every VizieR mirror tried (idia, china-vo, iucaa) were unreachable on 2026-10-31; the idia
mirror answered every request with a 302 to CDS. The SIMBAD mirror at simbad.harvard.edu works, and SIMBAD links each
object to the papers that catalogue it (has_ref), so catalogue membership is recovered from the bibcodes:

  LMC/SMC: Neugent et al. 2012 (LMC YSG+RSG), Yang et al. 2020 (SMC RSGs), Gonzalez-Fernandez et al. 2015 (both Clouds),
           Massey & Olsen 2003 (both Clouds), Neugent et al. 2020 (LMC RSG binaries), Davies et al. 2018 (both Clouds)
  Galaxy:  Messineo & Brown 2019 (K-M class-I stars in Gaia DR2)

Luminosity from 2MASS Ks (SIMBAD flux table) with BC_K = 2.69 (Davies, Crowther & Beasor 2018, MC RSGs),
mu_LMC = 18.477 (Pietrzynski+2019), mu_SMC = 18.977 (Graczyk+2020), A_K neglected (~0.03). Galactic stars: Gaia DR3
parallax distance where parallax_over_error > 5, else none; A_K neglected (a lower limit on L).

Writes work/sample_mc.csv, work/sample_gal.csv.
"""
import io
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

WORK = Path(__file__).resolve().parents[1] / "work"
TAP = "https://simbad.harvard.edu/simbad/sim-tap/sync"

BIBS_MC = {
    "2012ApJ...749..177N": "Neugent2012",
    "2020A&A...639A.116Y": "Yang2020",
    "2015A&A...578A...3G": "GF2015",
    "2003AJ....126.2867M": "MasseyOlsen2003",
    "2020ApJ...900..118N": "Neugent2020",
    "2018MNRAS.474.2116D": "Davies2018",
}
BIBS_GAL = {"2019AJ....158...20M": "MessineoBrown2019"}

BC_K = 2.69
MU = {"LMC": 18.477, "SMC": 18.977}
CENTRE = {"LMC": (80.89, -69.76, 9.0), "SMC": (13.19, -72.83, 5.0)}


def tap(query: str) -> pd.DataFrame:
    data = urllib.parse.urlencode(dict(request="doQuery", lang="adql", format="csv", query=query)).encode()
    for k in range(4):
        try:
            txt = urllib.request.urlopen(urllib.request.Request(TAP, data=data), timeout=300).read().decode()
            return pd.read_csv(io.StringIO(txt))
        except Exception as e:  # noqa: BLE001
            print("retry", k, e)
            time.sleep(10)
    raise RuntimeError("SIMBAD TAP failed")


def members(bibs: dict) -> pd.DataFrame:
    rows = []
    for bib, tag in bibs.items():
        q = f"""
        SELECT b.oid, b.main_id, b.ra, b.dec, b.otype, b.sp_type, b.plx_value
        FROM basic b JOIN has_ref h ON b.oid = h.oidref JOIN ref r ON r.oidbib = h.oidbibref
        WHERE r.bibcode = '{bib}'"""
        d = tap(q)
        d["cat"] = tag
        print(tag, len(d))
        rows.append(d)
    df = pd.concat(rows)
    cats = df.groupby("oid")["cat"].apply(lambda s: ";".join(sorted(set(s))))
    df = df.drop_duplicates("oid").set_index("oid")
    df["cats"] = cats
    return df.drop(columns="cat").reset_index()


def fluxes_and_ids(oids: list[int]) -> pd.DataFrame:
    out = []
    for i in range(0, len(oids), 400):
        chunk = ",".join(str(o) for o in oids[i:i + 400])
        f = tap(f"SELECT oidref AS oid, filter, flux FROM flux WHERE oidref IN ({chunk}) AND filter IN ('J','H','K','V','G')")
        piv = f.pivot_table(index="oid", columns="filter", values="flux", aggfunc="first")
        ids = tap(f"SELECT oidref AS oid, id FROM ident WHERE oidref IN ({chunk}) AND (id LIKE 'Gaia DR3 %' OR id LIKE '2MASS J%')")
        # Gaia ids stay strings until written: a 19-digit id joined against NaN becomes float64 and loses its last digits
        g = ids[ids.id.str.startswith("Gaia DR3")].assign(gaia_dr3=lambda d: d.id.str.split().str[-1])
        t = ids[ids.id.str.startswith("2MASS")].rename(columns={"id": "tmass"})
        piv = piv.join(g.drop_duplicates("oid").set_index("oid")["gaia_dr3"], how="outer")
        piv = piv.join(t.drop_duplicates("oid").set_index("oid")["tmass"], how="outer")
        out.append(piv)
    return pd.concat(out).reset_index()


def sep_deg(ra1, dec1, ra2, dec2):
    r1, d1, r2, d2 = map(np.radians, (ra1, dec1, ra2, dec2))
    return np.degrees(np.arccos(np.clip(np.sin(d1) * np.sin(d2) + np.cos(d1) * np.cos(d2) * np.cos(r1 - r2), -1, 1)))


def main():
    mc = members(BIBS_MC)
    mc = mc.merge(fluxes_and_ids(mc.oid.tolist()), on="oid", how="left")
    mc["galaxy"] = ""
    for gal, (ra0, de0, rad) in CENTRE.items():
        mc.loc[sep_deg(mc.ra, mc.dec, ra0, de0) < rad, "galaxy"] = gal
    mc = mc[mc.galaxy != ""].copy()
    mc["J_K"] = mc["J"] - mc["K"]
    mu = mc.galaxy.map(MU)
    mc["M_K"] = mc["K"] - mu
    mc["logL"] = (4.74 - (mc["M_K"] + BC_K)) / 2.5
    # Red supergiants only: Neugent 2012 also lists yellow supergiants; RSGs have (J-Ks) >~ 0.75
    mc["is_red"] = (mc["J_K"] >= 0.75) | mc.sp_type.fillna("").str.match(r"^(K[3-9]|M)")
    # Foreground dwarfs/giants: SIMBAD parallax (Gaia) significantly > 0 at MC distance is foreground
    mc["foreground"] = mc.plx_value.fillna(0) > 0.25
    mc["keep"] = mc.is_red & ~mc.foreground & (mc.logL >= 4.5)
    mc.to_csv(WORK / "sample_mc_all.csv", index=False)
    s = mc[mc.keep].copy()
    s.to_csv(WORK / "sample_mc.csv", index=False)
    print("MC members", len(mc), "red", int(mc.is_red.sum()), "foreground", int(mc.foreground.sum()))
    print(s.groupby("galaxy").size(), "kept logL>=4.5")
    print(mc[mc.is_red & ~mc.foreground].groupby("galaxy").size(), "red non-foreground, any L")

    gal = members(BIBS_GAL)
    gal = gal.merge(fluxes_and_ids(gal.oid.tolist()), on="oid", how="left")
    gal.to_csv(WORK / "sample_gal.csv", index=False)
    print("Galactic", len(gal))


if __name__ == "__main__":
    main()
