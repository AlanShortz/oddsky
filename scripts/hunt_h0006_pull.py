"""Hunt H-0006, step 1: stars whose warm-dust excess faded during NEOWISE (2014-2024).

Reads the H-0002 sky pass (`oddsky-sky-br3c3.sky.sky1_features`, AllWISE sources at |b| >= 10 deg; sky2_* is the fixed re-run) through
the `bq` CLI, then adds AllWISE positions (IRSA) and the Gaia DR3 sources within 6" of each flag.
color_end and w2_end are *changes* from the 2014-15 baseline (src/oddsky/sky/neowise_pixel.py), so "lost 60% of its
excess" is color_end < -0.6 * color_base.

Writes hunts/H-0006/flags.csv (one row per flag, Gaia columns prefixed gaia_) and lightcurves.csv (NEOWISE visits).
"""
import io
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pandas as pd

from oddsky.data.gaia import adql

here = Path("hunts/H-0006")
PROJECT = "oddsky-sky-br3c3"
WHERE = ("n_visits >= 12 AND base_scatter_w2 < 0.05 AND w1_base < 13 AND color_base > 0.25 "
         "AND w2_end > 0.2 AND color_end < -0.6 * color_base")


def bq(sql: str) -> pd.DataFrame:
    out = subprocess.run(["bq", f"--project_id={PROJECT}", "query", "--use_legacy_sql=false", "--format=csv",
                          "--max_rows=1000000", sql], check=True, capture_output=True, text=True).stdout
    return pd.read_csv(io.StringIO(out[out.index("allwise_cntr"):]), dtype={"allwise_cntr": "int64"})


def allwise_positions(ids: list[int]) -> pd.DataFrame:
    out = []
    for i in range(0, len(ids), 300):
        q = (f"SELECT cntr AS allwise_cntr, designation, ra, dec, ext_flg, cc_flags, nb FROM allwise_p3as_psd "
             f"WHERE cntr IN ({','.join(map(str, ids[i:i + 300]))})")
        r = httpx.post("https://irsa.ipac.caltech.edu/TAP/sync", data={"QUERY": q, "FORMAT": "csv", "LANG": "ADQL"},
                       timeout=300)
        r.raise_for_status()
        out.append(pd.read_csv(io.StringIO(r.text)))
    return pd.concat(out)


def gaia_match(r) -> dict:
    """Brightest Gaia DR3 source within 3" (source_id kept as a string: float64 rounds it onto a neighbour)."""
    q = (f"SELECT source_id, phot_g_mean_mag AS g, bp_rp, parallax, parallax_over_error AS poe, ruwe, pmra, pmdec, "
         f"in_qso_candidates AS qso_cand, in_galaxy_candidates AS gal_cand, teff_gspphot AS teff, mh_gspphot AS mh, "
         f"DISTANCE(POINT({r.ra},{r.dec}), POINT(ra,dec))*3600 AS sep FROM gaiadr3.gaia_source "
         f"WHERE 1=CONTAINS(POINT(ra,dec), CIRCLE({r.ra},{r.dec},{6 / 3600})) ORDER BY phot_g_mean_mag")
    for k in range(4):
        try:
            g = adql(q, timeout=60)
            break
        except Exception:  # noqa: BLE001
            time.sleep(5 * (k + 1))
    else:
        return {"allwise_cntr": r.allwise_cntr, "gaia_ok": False}
    rec = {"allwise_cntr": r.allwise_cntr, "gaia_ok": True, "gaia_n6": len(g)}
    near = g[g.sep.astype(float) < 3] if len(g) else g
    if len(near):
        m = near.iloc[0]
        rec.update({f"gaia_{k}": m[k] for k in g.columns})
        rec["gaia_source_id"] = str(int(m.source_id)) if not isinstance(m.source_id, str) else m.source_id
    return rec


def main() -> None:
    here.mkdir(parents=True, exist_ok=True)
    tbl = f"`{PROJECT}.sky.sky1_features`"
    flags = bq(f"SELECT * FROM {tbl} WHERE {WHERE}")
    print(len(flags), "flags", flush=True)
    lc = bq(f"SELECT l.* FROM `{PROJECT}.sky.sky1_lightcurves` l JOIN (SELECT allwise_cntr FROM {tbl} WHERE {WHERE}) "
            f"USING (allwise_cntr) ORDER BY allwise_cntr, t")
    lc.to_csv(here / "lightcurves.csv", index=False)
    flags = flags.merge(allwise_positions(flags.allwise_cntr.tolist()), on="allwise_cntr", how="left")
    with ThreadPoolExecutor(8) as ex:
        g = pd.DataFrame(list(ex.map(gaia_match, flags.itertuples())))
    flags.merge(g, on="allwise_cntr", how="left").to_csv(here / "flags.csv", index=False)
    print("wrote", here / "flags.csv")


if __name__ == "__main__":
    main()
