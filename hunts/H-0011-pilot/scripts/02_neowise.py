"""H-0011 pilot, step 2: NEOWISE-R (2013-12 to 2024-07) and AllWISE multi-epoch (2010) single exposures, in bulk.

IRSA TAP with an uploaded position list (pyvo), 3" cone, chunks of 40 stars, 4 threads. Each exposure keeps only the
detection nearest the catalogue position. The same quality cuts and visit binning as src/oddsky/data/neowise.py are
then applied (quality_cuts, visits; lowercase cc_flags tolerated, see visits_neo), so visit flags carry 'saturated' (W1 < 8, W2 < 7) and 'saturated_pixels'
(w?sat > 0.05). AllWISE-MEP exposures (cryogenic + 3-band + post-cryo 2010-2011) have no ph_qual/snr/w?sat columns,
so they get only the cuts that apply (qi_fact, saa_sep, moon_masked, nb, finite, sigma < 0.25). Their cc_flags are the
AllWISE source flags (constant per star, not per exposure), so halo (h) and ghost (o) flags are tolerated there.

usage: 02_neowise.py mc|gal|cal
Writes work/neowise_exp_<s>.parquet (raw exposures), work/neowise_visits_<s>.parquet (visit light curves).
"""
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import pyvo
from astropy.table import Table

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from oddsky.data import neowise  # noqa: E402
from oddsky.data.provenance import Provenance  # noqa: E402

WORK = Path(__file__).resolve().parents[1] / "work"
TAP = "https://irsa.ipac.caltech.edu/TAP"
R_DEG = 3.0 / 3600

Q_NEO = """SELECT u.sid, u.ra0, u.dec0, n.ra, n.dec, n.mjd, n.w1mpro, n.w1sigmpro, n.w2mpro, n.w2sigmpro, n.qual_frame,
n.qi_fact, n.saa_sep, n.moon_masked, n.cc_flags, n.ph_qual, n.w1sat, n.w2sat, n.nb, n.na, n.w1snr, n.w2snr,
n.w1rchi2, n.w2rchi2
FROM neowiser_p1bs_psd n, TAP_UPLOAD.pos u
WHERE CONTAINS(POINT('ICRS', n.ra, n.dec), CIRCLE('ICRS', u.ra0, u.dec0, {r})) = 1"""

Q_MEP = """SELECT u.sid, u.ra0, u.dec0, n.ra, n.dec, n.mjd, n.w1mpro_ep, n.w1sigmpro_ep, n.w2mpro_ep, n.w2sigmpro_ep,
n.qi_fact, n.saa_sep, n.moon_masked, n.cc_flags, n.nb, n.na, n.w1rchi2_ep, n.w2rchi2_ep
FROM allwise_p3as_mep n, TAP_UPLOAD.pos u
WHERE CONTAINS(POINT('ICRS', n.ra, n.dec), CIRCLE('ICRS', u.ra0, u.dec0, {r})) = 1"""


def run(q: str, chunk: pd.DataFrame) -> pd.DataFrame:
    t = Table.from_pandas(pd.DataFrame(dict(sid=chunk.oid.astype(int), ra0=chunk.ra, dec0=chunk.dec)))
    svc = pyvo.dal.TAPService(TAP)
    for k in range(4):
        try:
            return svc.run_sync(q.format(r=R_DEG), uploads={"pos": t}, maxrec=50_000_000).to_table().to_pandas()
        except Exception as e:  # noqa: BLE001
            print("retry", k, str(e)[:200], flush=True)
            time.sleep(20 * (k + 1))
    raise RuntimeError("IRSA TAP failed")


def nearest_per_exposure(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["sep"] = 3600 * np.hypot((d.ra - d.ra0) * np.cos(np.radians(d.dec0)), d.dec - d.dec0)
    d = d.sort_values("sep").drop_duplicates(["sid", "mjd"])
    return d.sort_values(["sid", "mjd"])


def fetch(sample: pd.DataFrame, q: str, tag: str) -> pd.DataFrame:
    out = WORK / f"{tag}.parquet"
    if out.exists():
        return pd.read_parquet(out)
    chunks = [sample.iloc[i:i + 40] for i in range(0, len(sample), 40)]
    parts = []
    with ThreadPoolExecutor(4) as ex:
        futs = {ex.submit(run, q, c): i for i, c in enumerate(chunks)}
        for n, f in enumerate(as_completed(futs)):
            parts.append(f.result())
            print(tag, f"{n + 1}/{len(chunks)}", flush=True)
    df = nearest_per_exposure(pd.concat(parts, ignore_index=True))
    for c in ("moon_masked", "cc_flags", "ph_qual"):
        if c in df:
            df[c] = df[c].astype(str)
    df.to_parquet(out)
    return df


def visits_neo(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sid, g in df.groupby("sid"):
        prov = Provenance(archive="IRSA TAP neowiser_p1bs_psd", query={})
        g = g.reset_index(drop=True).copy()
        # Lowercase cc_flags (h halo, d spike, o ghost, p persistence) mean "contaminated by a neighbour", uppercase
        # mean "likely spurious". For the bright RSGs in crowded Cloud fields the lowercase flags remove whole light
        # curves, so they are tolerated here (and counted); uppercase still fails neowise.quality_cuts.
        g["cc_contam"] = g.cc_flags.str.contains("[hdop]", regex=True)
        g["cc_flags"] = g.cc_flags.str.replace("[hdop]", "0", regex=True)
        for band in ("W1", "W2"):
            v = neowise.visits(neowise.quality_cuts(g, band, prov), band)
            if len(v):
                v["sid"] = sid
                rows.append(v)
    return pd.concat(rows, ignore_index=True)


def visits_mep(df: pd.DataFrame) -> pd.DataFrame:
    """AllWISE-MEP (2010): cuts that exist for this table, then the same visit binning."""
    d = df.rename(columns={"w1mpro_ep": "w1mpro", "w1sigmpro_ep": "w1sigmpro", "w2mpro_ep": "w2mpro",
                           "w2sigmpro_ep": "w2sigmpro"}).copy()
    d["w1sat"] = 0.0
    d["w2sat"] = 0.0
    rows = []
    for sid, g in d.groupby("sid"):
        for band, idx in (("W1", 0), ("W2", 1)):
            b = band.lower()
            m = ((g.qi_fact > 0) & (g.saa_sep > 0) & (g.moon_masked.str.zfill(4).str[idx] == "0")
                 & g.cc_flags.str.zfill(4).str[idx].isin(["0", "h", "o"]) & (g.nb == 1) & np.isfinite(g[f"{b}mpro"].astype(float))
                 & (g[f"{b}sigmpro"].astype(float) < 0.25))
            v = neowise.visits(g[m].reset_index(drop=True), band)
            if len(v):
                v["sid"] = sid
                v["survey"] = "WISE_MEP"
                rows.append(v)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def main(which: str):
    sample = pd.read_csv(WORK / f"sample_{which}.csv", dtype={"gaia_dr3": "Int64"})
    sample = sample.dropna(subset=["ra", "dec"])
    neo = fetch(sample, Q_NEO, f"neowise_exp_{which}")
    print("NEOWISE exposures", len(neo), "stars", neo.sid.nunique(), flush=True)
    mep = fetch(sample, Q_MEP, f"allwise_mep_exp_{which}")
    print("AllWISE-MEP exposures", len(mep), "stars", mep.sid.nunique(), flush=True)
    v = pd.concat([visits_neo(neo), visits_mep(mep)], ignore_index=True)
    v.to_parquet(WORK / f"neowise_visits_{which}.parquet")
    print("visits", len(v), v.groupby(["survey", "band"]).sid.nunique().to_dict())


if __name__ == "__main__":
    main(sys.argv[1])
