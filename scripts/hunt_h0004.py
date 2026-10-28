"""Hunt H-0004, step 1: the pool of stars that might go dark.

Pool A: Tisserand+2020 WISE/2MASS-selected R CrB candidates (VizieR J/A+A/635/A14/table2, 2,356).
Pool B: Gaia DR3 2014-17 skewed faders from hunt H-0003 (hunts/H-0003/scored.csv).

Exclusions (kept in the file with a reason, so the funnel is auditable):
  known RCB / dLHdC (Karambelkar+2022 J/A+A/667/A84; SIMBAD otype RC*), Karambelkar+2024 spectroscopic
  classifications (hunts/H-0004/ext/k24/, from Zenodo 10.5281/zenodo.12683155, when present).
Enrichment: SIMBAD main_id/otype (3"), Gaia DR3 source (2"), Karambelkar+2024 priority when present.

Run from the repo root:  .venv/bin/python scripts/hunt_h0004.py
"""
from __future__ import annotations

import io
import time
from pathlib import Path

import numpy as np
import pandas as pd

here = Path("hunts/H-0004")
ext = here / "ext"


def read_vizier_tsv(path: Path) -> pd.DataFrame:
    lines = [ln for ln in path.read_text().splitlines() if ln and not ln.startswith("#")]
    header = lines[0].split("\t")
    body = [ln for ln in lines[3:] if ln.strip()]
    df = pd.read_csv(io.StringIO("\n".join(body)), sep="\t", names=header, dtype=str, keep_default_na=False)
    return df.apply(lambda c: c.str.strip())


def sep_arcsec(ra1, dec1, ra2, dec2):
    ra1, dec1, ra2, dec2 = (np.radians(np.asarray(x, float)) for x in (ra1, dec1, ra2, dec2))
    d = np.sin(dec1) * np.sin(dec2) + np.cos(dec1) * np.cos(dec2) * np.cos(ra1 - ra2)
    return np.degrees(np.arccos(np.clip(d, -1, 1))) * 3600


def nearest(pool: pd.DataFrame, cat: pd.DataFrame, radius: float) -> pd.Series:
    """For each pool row, the index of the nearest catalogue row within `radius` arcsec, else -1."""
    out = np.full(len(pool), -1)
    if cat.empty:
        return pd.Series(out, index=pool.index)
    cra, cdec = cat.ra.to_numpy(float), cat.dec.to_numpy(float)
    for i, (ra, dec) in enumerate(zip(pool.ra, pool.dec, strict=True)):
        near = np.abs(cdec - dec) < radius / 3600 + 1e-6
        if not near.any():
            continue
        s = sep_arcsec(ra, dec, cra[near], cdec[near])
        k = int(np.argmin(s))
        if s[k] <= radius:
            out[i] = np.flatnonzero(near)[k]
    return pd.Series(out, index=pool.index)


# ---------------------------------------------------------------- Pool A: Tisserand+2020
t20 = read_vizier_tsv(ext / "tisserand2020_table2.tsv")
num = lambda c: pd.to_numeric(t20[c], errors="coerce")  # noqa: E731
a = pd.DataFrame({
    "id": "T20-" + t20["ID"].astype(int).astype(str), "pool": "A", "t20_id": t20["ID"].astype(int),
    "wise_id": t20["WiseID"], "ra": num("RAJ2000"), "dec": num("DEJ2000"), "glon": num("GLON"), "glat": num("GLAT"),
    "w1": num("[3.4]"), "w2": num("[4.6]"), "w3": num("[12]"), "w4": num("[22]"),
    "j": num("Jmag"), "h": num("Hmag"), "k": num("Kmag"),
    "t20_simbad_name": t20["SName"], "t20_simbad_type": t20["SType"], "t20_sp_class": t20["SSpClass"],
})

# ---------------------------------------------------------------- Pool B: H-0003 Gaia faders
b = pd.DataFrame()
h3 = Path("hunts/H-0003/scored.csv")
if h3.exists():
    s3 = pd.read_csv(h3)
    keep = s3.rcb_like.astype(bool) | ((s3.depth >= 1.5) & (s3.fade_rate > s3.rise_rate))
    s3 = s3[keep]
    b = pd.DataFrame({
        "id": "GDR3-" + s3.source_id.astype(str), "pool": "B", "source_id": s3.source_id.astype("int64"),
        "ra": s3.ra, "dec": s3.dec, "glon": s3.l, "glat": s3.b, "gaia_g": s3.g_mag, "bp_rp": s3.bp_rp,
        "parallax": s3.parallax, "poe": s3.poe, "ruwe": s3.ruwe, "h3_depth": s3.depth, "h3_rcb_like": s3.rcb_like,
    })

pool = pd.concat([a, b], ignore_index=True)
pool["excluded_reason"] = ""
print(f"pool A {len(a)}, pool B {len(b)}")

# ---------------------------------------------------------------- known RCB / dLHdC (Karambelkar+2022)
k22 = read_vizier_tsv(ext / "karambelkar2022_objects.tsv")
from astropy.coordinates import SkyCoord  # noqa: E402

_c = SkyCoord(k22["RAJ2000"].tolist(), k22["DEJ2000"].tolist(), unit=("hourangle", "deg"))
k22 = pd.DataFrame({"name": k22["Name"], "ra": _c.ra.deg, "dec": _c.dec.deg, "cls": k22["Class"]})
m = nearest(pool, k22, 5.0)
hit = m >= 0
pool.loc[hit, "excluded_reason"] = "known " + k22.cls.to_numpy()[m[hit]] + " (Karambelkar+2022): " + k22.name.to_numpy()[m[hit]]
print("known RCB/dLHdC matches:", int(hit.sum()))

# ---------------------------------------------------------------- Karambelkar+2024 (Zenodo 10.5281/zenodo.12683155)
# lc-pri: PGIR J-band light-curve class (A = non-periodic variations ... G = no usable PGIR data);
# col-pri: WISE/2MASS colour group (1-a best ... 3-b worst). Classification: NIR spectrum of 453 candidates.
k24_dir = ext / "k24"
pool["k24_lc_pri"] = ""
pool["k24_col_pri"] = ""
pool["k24_class"] = ""
if (k24_dir / "tisserand2020_catalog_pgir_priorities.csv").exists():
    pr = pd.read_csv(k24_dir / "tisserand2020_catalog_pgir_priorities.csv", dtype=str)
    pr["t20_id"] = pd.to_numeric(pr["Toi_id"], errors="coerce")
    pool["k24_lc_pri"] = pool.t20_id.map(pr.set_index("t20_id")["lc-pri"]).fillna("")
    pool["k24_col_pri"] = pool.t20_id.map(pr.set_index("t20_id")["col-pri"]).fillna("")
    cl = pd.read_csv(k24_dir / "classifications_table.csv", dtype=str)
    cl["t20_id"] = pd.to_numeric(cl["Name"].str.extract(r"WISE-ToI-(\d+)")[0], errors="coerce")
    cl = cl.dropna(subset=["t20_id"]).drop_duplicates("t20_id")
    pool["k24_class"] = pool.t20_id.map(cl.set_index("t20_id")["Classification"]).fillna("")
    # "RCB-cand" stays in the pool: those are exactly the stars whose first decline would settle it.
    spec = pool.k24_class.ne("") & pool.k24_class.ne("RCB-cand") & pool.excluded_reason.eq("")
    pool.loc[spec, "excluded_reason"] = "classified by Karambelkar+2024: " + pool.loc[spec, "k24_class"]
    print("K24 priorities:", int(pool.k24_lc_pri.ne("").sum()), "spectroscopic exclusions:", int(spec.sum()),
          "RCB-cand kept:", int(pool.k24_class.eq("RCB-cand").sum()))

# ---------------------------------------------------------------- SIMBAD
# Pool A carries SIMBAD name/type from Tisserand+2020 (2018 epoch); only pool B needs a lookup. A 2026
# refresh for the picks happens in the vet step, where RC* entries added since 2018 are caught.
pool["simbad_main_id"] = pool.get("t20_simbad_name", "")
pool["simbad_otype"] = pool.get("t20_simbad_type", "")
rc = pool.simbad_otype.fillna("").str.strip().isin(["RC*", "RCB", "RC?"]) & pool.excluded_reason.eq("")
pool.loc[rc, "excluded_reason"] = "SIMBAD RC*: " + pool.loc[rc, "simbad_main_id"]
print("SIMBAD RC* exclusions (2018 types):", int(rc.sum()))

pool["ztf_footprint"] = pool.dec > -30
pool = pool.sort_values(["pool", "k24_lc_pri", "k24_col_pri", "dec"], ascending=[True, True, True, False]).reset_index(drop=True)


def write(pool: pd.DataFrame) -> pd.DataFrame:
    pool.to_csv(here / "pool.csv", index=False)
    cand = pool[pool.excluded_reason.eq("")]
    cand.to_csv(here / "candidates.csv", index=False)
    return cand


cand = write(pool)
print(f"pool {len(pool)} -> candidates {len(cand)} (north of -30: {int(cand.ztf_footprint.sum())}, "
      f"south: {int((~cand.ztf_footprint).sum())}); candidates.csv written, fetch can start")

# ---------------------------------------------------------------- Gaia DR3: brightest source within 2" (per-star cones)
# Anonymous TAP uploads are refused by the archive (release 3.15), and the AllWISE best-neighbour table
# misses most of these dusty stars, so this is one small cone per star, three at a time.
from concurrent.futures import ThreadPoolExecutor  # noqa: E402

from oddsky.data import gaia  # noqa: E402

GCOLS = ["source_id", "phot_g_mean_mag", "bp_rp", "parallax", "parallax_over_error", "ruwe"]


def gaia_match(row):
    for attempt in range(3):
        try:
            cone, _ = gaia.cone(row.ra, row.dec, 3.0)
            break
        except Exception:  # noqa: BLE001
            time.sleep(10 * (attempt + 1))
            cone = pd.DataFrame()
    if cone.empty:
        return {"id": row.id}
    close = cone[cone.sep_arcsec <= 2.0]
    tgt = (close.sort_values("phot_g_mean_mag") if not close.empty else cone).iloc[0]
    out = {"id": row.id, "gaia_sep": float(tgt.sep_arcsec), "n_gaia_3arcsec": int(len(cone))}
    out.update({c: tgt[c] for c in GCOLS if c in tgt})
    return out


need = pool[pool.source_id.isna()] if "source_id" in pool else pool
print("Gaia cones to run:", len(need), flush=True)
with ThreadPoolExecutor(3) as ex:
    recs = list(ex.map(gaia_match, need.itertuples()))
gg = pd.DataFrame(recs).set_index("id")
gg = gg.rename(columns={"phot_g_mean_mag": "gaia_g", "parallax_over_error": "poe"})
for c in ("source_id", "gaia_g", "bp_rp", "parallax", "poe", "ruwe", "gaia_sep", "n_gaia_3arcsec"):
    if c not in gg:
        continue
    if c in pool:
        pool[c] = pool[c].where(pool[c].notna(), pool.id.map(gg[c]))
    else:
        pool[c] = pool.id.map(gg[c])
print("Gaia matches:", int(pool.source_id.notna().sum()))

# absolute magnitude for the luminosity sanity check downstream
with np.errstate(invalid="ignore", divide="ignore"):
    good_plx = pool.poe > 5
    pool["abs_g"] = np.where(good_plx, pool.gaia_g - 5 * np.log10(1000 / pool.parallax.clip(lower=1e-3)) + 5, np.nan)
cand = write(pool)
print(f"final: pool {len(pool)} -> candidates {len(cand)}")
print(pool.excluded_reason.str.split(":").str[0].value_counts().to_string())
