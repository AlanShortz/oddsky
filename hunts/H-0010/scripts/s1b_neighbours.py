"""s1b: every Gaia DR3 source within 6" of each of the 67 (VizieR I/355/gaiadr3 on the vizier.idia.ac.za mirror; the ESA TAP
cone queries in s1 took over a minute each and stalled). Source ids kept as strings.
Run from the repo root: uv run python -I hunts/H-0010/scripts/s1b_neighbours.py
Writes hunts/H-0010/data/neighbours.csv (one row per neighbour; the target itself excluded)."""
import io
import os
import sys
import time

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, targets  # noqa: E402

VIZ = "https://vizier.idia.ac.za/viz-bin/asu-tsv"
OUT = "Source,RA_ICRS,DE_ICRS,Gmag,BPmag,RPmag,BP-RP,RUWE,VarFlag,EpochPh"


def cone(ra, dec):
    for _ in range(4):
        try:
            q = requests.get(VIZ, params={"-source": "I/355/gaiadr3", "-c": f"{ra} {dec}", "-c.rs": 6, "-out": OUT,
                                          "-out.add": "_r", "-out.max": 200}, timeout=120)
            q.raise_for_status()
            lines = [ln for ln in q.text.splitlines() if ln and not ln.startswith("#")]
            return pd.read_csv(io.StringIO("\n".join([lines[0]] + lines[3:])), sep="\t", dtype={"Source": str})
        except Exception as e:  # noqa: BLE001
            print("retry", type(e).__name__)
            time.sleep(10)
    raise RuntimeError("vizier failed")


def main():
    rows = []
    for r in targets().itertuples():
        d = cone(r.ra, r.dec)
        d["Source"] = d.Source.str.strip()
        assert (d.Source == r.source_id).any(), r.source_id
        d = d[d.Source != r.source_id].rename(columns={"Source": "nb_source_id", "RA_ICRS": "ra", "DE_ICRS": "dec", "Gmag": "phot_g_mean_mag",
                                                         "BPmag": "phot_bp_mean_mag", "RPmag": "phot_rp_mean_mag", "BP-RP": "bp_rp",
                                                         "RUWE": "ruwe", "VarFlag": "phot_variable_flag", "_r": "sep"})
        for c in ("ra", "dec", "phot_g_mean_mag", "phot_bp_mean_mag", "phot_rp_mean_mag", "bp_rp", "ruwe", "sep"):
            d[c] = pd.to_numeric(d[c].astype(str).str.strip(), errors="coerce")
        d["phot_variable_flag"] = d.phot_variable_flag.astype(str).str.strip()
        d["has_epoch_photometry"] = d.EpochPh.astype(str).str.strip().eq("1")
        d["target"] = r.source_id
        rows.append(d.drop(columns="EpochPh"))
    nbs = pd.concat(rows, ignore_index=True)
    nbs.to_csv(os.path.join(DATA, "neighbours.csv"), index=False)
    print(f"neighbours within 6\": {len(nbs)}; within 2\": {(nbs.sep < 2).sum()}; VARIABLE: {(nbs.phot_variable_flag == 'VARIABLE').sum()}; "
          f"with epoch photometry: {nbs.has_epoch_photometry.sum()}")


if __name__ == "__main__":
    main()
