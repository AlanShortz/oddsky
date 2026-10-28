"""Hunt H-0002 vetting: turn sky-pass candidates into a ranked, Skeptic-checked shortlist.

python scripts/hunt_h0002_vet.py <run>    (reads hunts/H-0002/runs/<run>/candidates/*.parquet, downloaded from GCS)
"""
import glob
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from oddsky.data.gaia import adql

run = sys.argv[1]
here = Path(f"hunts/H-0002/runs/{run}")
cand = pd.concat([pd.read_parquet(f) for f in glob.glob(str(here / "candidates/*.parquet"))], ignore_index=True)
cand = cand[cand.ra.notna()].copy()
print(len(cand), "candidates with positions", flush=True)

# 1. Blend pairs: two flagged stars within 30" that brightened on the same visit are one event seen twice.
cand["pair_with"] = None
xyz = np.c_[np.cos(np.radians(cand.dec)) * np.cos(np.radians(cand.ra)),
            np.cos(np.radians(cand.dec)) * np.sin(np.radians(cand.ra)), np.sin(np.radians(cand.dec))]
for i in range(len(cand)):
    sep = np.degrees(np.arccos(np.clip(xyz @ xyz[i], -1, 1))) * 3600
    near = np.where((sep < 30) & (sep > 0) & (np.abs(cand.t_rise.to_numpy() - cand.t_rise.iloc[i]) < 30))[0]
    if len(near):
        j = near[np.argmax(cand.w2_rise.to_numpy()[near])]
        if cand.w2_rise.iloc[j] > cand.w2_rise.iloc[i]:
            cand.iloc[i, cand.columns.get_loc("pair_with")] = int(cand.allwise_cntr.iloc[j])


def gaia(row):
    q = (f"SELECT source_id, phot_g_mean_mag AS g, bp_rp, parallax, parallax_over_error AS poe, ruwe, teff_gspphot AS teff, "
         f"DISTANCE(POINT({row.ra},{row.dec}), POINT(ra,dec))*3600 AS sep FROM gaiadr3.gaia_source "
         f"WHERE 1=CONTAINS(POINT(ra,dec), CIRCLE({row.ra},{row.dec},{8 / 3600})) ORDER BY phot_g_mean_mag")
    for _ in range(3):
        try:
            return row.allwise_cntr, adql(q, timeout=60)
        except Exception:  # noqa: BLE001
            time.sleep(3)
    return row.allwise_cntr, pd.DataFrame()


rows = []
with ThreadPoolExecutor(4) as ex:
    for cntr, g in ex.map(gaia, cand.itertuples()):
        r = {"allwise_cntr": cntr, "gaia_n8": len(g)}
        if len(g):
            close = g[g.sep < 2.0]
            m = (close.sort_values("g").iloc[0] if len(close) else None)
            if m is not None:
                # source_id from the int64 column: a mixed-dtype row is float64 and rounds onto a neighbour's id
                sid = int(close.sort_values("g")["source_id"].iloc[0])
                r.update(gaia_id=str(sid), G=m.g, bp_rp=m.bp_rp, parallax=m.parallax, poe=m.poe, ruwe=m.ruwe, teff=m.teff, sep=m.sep)
                others = g[g.source_id != sid]
                bright = others[others.g < m.g + 2.5]
                r["blend_n"] = int(len(bright))
                r["blend_min_sep"] = float(bright.sep.min()) if len(bright) else np.nan
        rows.append(r)
g = pd.DataFrame(rows)
v = cand.merge(g, on="allwise_cntr", how="left")
v["absG"] = v.G + 5 * np.log10(v.parallax.clip(lower=1e-3) / 100)
# Dust already present in 2010? A bare photosphere has W1-W3 ~ 0 and W1-W4 ~ 0 (FGK).
v["w1_w3_allwise"] = v.w1_base - v.w3mpro_allwise
v["prior_dust"] = v.w1_w3_allwise > 0.5
v["stellar"] = v.poe > 5
v["sunlike"] = v.stellar & v.bp_rp.between(0.5, 1.6) & v.absG.between(2.0, 7.5) & (v.ruwe < 1.4)
v["clean"] = v.blend_n.fillna(0).eq(0) & v.pair_with.isna()
v["tier"] = np.select(
    [v.sunlike & v.clean & ~v.prior_dust, v.stellar & v.clean & ~v.prior_dust, v.stellar & v.clean, v.clean & ~v.stellar.fillna(False)],
    ["A: Sun-like, clean, no prior dust", "B: other star, clean, no prior dust", "C: star with dust before 2010",
     "E: no parallax (galaxy/AGN? nuclear flare)"], "D: blend or pair")
v.to_parquet(here / "vetted.parquet", index=False)
print(v.tier.value_counts().to_string(), flush=True)
