"""Zwicky Transient Facility light curves (2018-, dec > -30, saturates brighter than ~12.5)."""

from __future__ import annotations

import io

import pandas as pd

from . import series
from .http import request
from .provenance import Provenance

API = "https://irsa.ipac.caltech.edu/cgi-bin/ZTF/nph_light_curves"


def lightcurve(ra: float, dec: float, radius_arcsec: float = 2.0) -> tuple[pd.DataFrame, Provenance]:
    params = {"POS": f"CIRCLE {ra} {dec} {radius_arcsec / 3600:.6f}", "BANDNAME": "g,r,i",
              "FORMAT": "csv", "BAD_CATFLAGS_MASK": "32768"}
    prov = Provenance(archive="IRSA ZTF light curve service", query=params)
    if dec < -31:
        prov.status = "empty"
        prov.notes.append("south of ZTF's footprint")
        return series.empty(), prov
    r = request("GET", API, params=params, timeout=180)
    raw = pd.read_csv(io.StringIO(r.text))
    prov.rows_raw = len(raw)
    if raw.empty:
        prov.status = "empty"
        prov.notes.append("no ZTF source (target may be brighter than ZTF saturation, ~12.5 mag)")
        return series.empty(), prov
    flag = (raw["catflags"] != 0).map({True: "catflags", False: ""})
    df = pd.DataFrame(dict(t_mjd=raw["mjd"], mag=raw["mag"], err=raw["magerr"],
                           band="ZTF_" + raw["filtercode"].str[-1], survey="ZTF", flag=flag,
                           camera=raw["field"].astype(str) + ":" + raw["ccdid"].astype(str)))
    if raw["oid"].nunique() > 1:
        prov.notes.append(f"{raw['oid'].nunique()} ZTF object IDs merged (one per field/filter)")
    df = series.normalize(df)
    prov.rows_kept = int((df.flag == "").sum())
    return df, prov
