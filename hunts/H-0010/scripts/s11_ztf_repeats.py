"""s11: ZTF (2018-2025, dec > -31) as a repeat test. A lens does not repeat; YSO bursts, Be-star outbursts, dwarf novae do.
For every source not already identified as a catalogued lens, within 1.5": per band and field/CCD (camera), the median and
robust scatter of clean points (catflags 0); a brightening night is >= max(0.3 mag, 5 sigma) brighter than that median; a
repeat is >= 2 such nights within 30 d (not single outliers). Also the total range (5th-95th percentile).
Run from the repo root: uv run python -I hunts/H-0010/scripts/s11_ztf_repeats.py
Writes hunts/H-0010/data/ztf_repeats.csv."""
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, mjd2date, targets  # noqa: E402

from oddsky.data import ztf  # noqa: E402


def main():
    T = targets()
    x = pd.read_csv(os.path.join(DATA, "xmatch.csv"), dtype={"source_id": str})
    known = set(x[x.ref_intime.notna() | x.gaia_alert.notna()].source_id)
    rows = []
    for r in T.itertuples():
        if r.source_id in known or r.dec < -31:
            continue
        for k in range(3):
            try:
                df, prov = ztf.lightcurve(r.ra, r.dec, radius_arcsec=1.5)
                break
            except Exception as e:  # noqa: BLE001
                df, prov = None, str(e)[:80]
                time.sleep(15)
        if df is None:
            rows.append(dict(source_id=r.source_id, ztf_status=f"ERR {prov}"))
            continue
        df = df[(df.flag == "") & np.isfinite(df.mag)]
        if df.empty:
            rows.append(dict(source_id=r.source_id, ztf_status="no ZTF source within 1.5\""))
            print(r.source_id, "no ZTF", flush=True)
            continue
        rec = dict(source_id=r.source_id, ztf_status="ok", ztf_n=len(df),
                   ztf_span=f"{mjd2date(df.t_mjd.min())}..{mjd2date(df.t_mjd.max())}")
        bursts, ranges = [], []
        for (band, cam), g in df.groupby(["band", "camera"]):
            if len(g) < 20:
                continue
            med = g.mag.median()
            sig = 1.4826 * np.median(np.abs(g.mag - med))
            ranges.append(f"{band[-1]}:{g.mag.quantile(0.95) - g.mag.quantile(0.05):.2f}")
            thr = max(0.3, 5 * sig)
            b = g[g.mag < med - thr].sort_values("t_mjd")
            nights = np.unique(np.floor(b.t_mjd.values))
            for n0 in nights:
                close = nights[(nights > n0) & (nights - n0 < 30)]
                if len(close):
                    sel = b[(b.t_mjd >= n0) & (b.t_mjd < n0 + 31)]
                    bursts.append(f"{band[-1]}@{cam} {mjd2date(n0)} {(sel.mag - med).min():+.2f}")
                    break
        rec["ztf_range_5_95"] = ";".join(sorted(set(ranges)))
        rec["ztf_repeats"] = ";".join(bursts)
        rows.append(rec)
        print(r.source_id, rec["ztf_n"], rec["ztf_range_5_95"], "| bursts:", rec["ztf_repeats"] or "-", flush=True)
    pd.DataFrame(rows).to_csv(os.path.join(DATA, "ztf_repeats.csv"), index=False)


if __name__ == "__main__":
    main()
