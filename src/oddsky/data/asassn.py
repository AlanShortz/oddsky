"""ASAS-SN Sky Patrol (2012-): V then g, whole sky, ~15" pixels.

The service hits a single host and goes down for maintenance; Oddsky treats that as a normal
state of the world and says so in provenance instead of failing.
"""

from __future__ import annotations

import contextlib
import io

import pandas as pd

from . import series
from .provenance import Provenance


def lightcurve(ra: float, dec: float, radius_arcsec: float = 5.0) -> tuple[pd.DataFrame, Provenance]:
    prov = Provenance(archive="ASAS-SN Sky Patrol (pyasassn)", query={"ra": ra, "dec": dec, "radius_arcsec": radius_arcsec})
    try:
        from pyasassn.client import SkyPatrolClient
    except ImportError:
        prov.status = "unavailable"
        prov.notes.append("install oddsky[asassn] for ASAS-SN light curves")
        return series.empty(), prov
    try:
        with contextlib.redirect_stdout(io.StringIO()):  # the client prints a banner; stdout is sacred under MCP
            client = SkyPatrolClient()
            lcs = client.cone_search(ra, dec, radius_arcsec, units="arcsec", download=True, threads=1)
        raw = lcs.data
    except Exception as e:  # noqa: BLE001 - any failure of a remote service is "unavailable"
        prov.status = "unavailable"
        prov.notes.append(f"Sky Patrol light-curve service failed: {type(e).__name__}: {e}"[:300])
        return series.empty(), prov
    prov.rows_raw = len(raw)
    if raw.empty:
        prov.status = "empty"
        return series.empty(), prov
    flag = pd.Series("", index=raw.index)
    flag[raw["quality"] != "G"] = "quality"
    flag[raw["mag_err"] >= 99] = "upper_limit"
    df = pd.DataFrame(dict(t_mjd=raw["jd"] - 2400000.5, mag=raw["mag"], err=raw["mag_err"],
                           band=raw["phot_filter"], survey="ASAS-SN", flag=flag, camera=raw["camera"].astype(str)))
    df = series.normalize(df)
    prov.rows_kept = int((df.flag == "").sum())
    return df, prov
