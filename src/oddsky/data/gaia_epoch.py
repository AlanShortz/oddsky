"""Gaia DR3 epoch photometry (2014-07 to 2017-05): per-transit G, BP and RP for ~10 million variables.

Three bands observed within seconds of each other on every transit make a built-in colour test:
real dimming by dust is redder (BP drops more than RP); a neighbour sliding in and out of the
photometric window as the scan angle changes is not bound by that physics.
"""

from __future__ import annotations

import io
import zipfile

import numpy as np
import pandas as pd

from . import series
from .http import request
from .provenance import Provenance

DATALINK = "https://gea.esac.esa.int/data-server/data"
GAIA_T0_MJD = 55197.0  # Gaia epoch-photometry times are BJD(TCB) - 2455197.5


def fetch(source_ids: list[int], chunk: int = 50) -> dict[int, pd.DataFrame]:
    """Epoch photometry for many sources at once (the server takes at most 50 ids per request).
    Sources without epoch photometry are simply absent."""
    out: dict[int, pd.DataFrame] = {}
    for i in range(0, len(source_ids), chunk):
        ids = ",".join(str(int(s)) for s in source_ids[i:i + chunk])
        r = request("POST", DATALINK, timeout=300, data=dict(
            RETRIEVAL_TYPE="EPOCH_PHOTOMETRY", ID=ids, FORMAT="csv", DATA_STRUCTURE="DATAMODEL_STANDARD",
            RELEASE="Gaia DR3", VALID_DATA="false"))
        if not r.content:
            continue
        if not zipfile.is_zipfile(io.BytesIO(r.content)):
            # A single source comes back as bare CSV rather than a zip.
            raw = pd.read_csv(io.StringIO(r.text), comment="#")
            if not raw.empty and "source_id" in raw:
                for sid, grp in raw.groupby("source_id"):
                    out[int(sid)] = to_series(grp)
            continue
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            for name in z.namelist():
                raw = pd.read_csv(io.StringIO(z.read(name).decode()), comment="#")
                if raw.empty:
                    continue
                out[int(raw.source_id.iloc[0])] = to_series(raw)
    return out


def to_series(raw: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for band, p in (("G", "g_transit"), ("BP", "bp"), ("RP", "rp")):
        tcol = "g_transit_time" if band == "G" else f"{p}_obs_time"
        mag = raw[f"{p}_mag"].astype(float)
        foe = raw[f"{p}_flux_over_error"].astype(float)
        err = 1.0857 / foe.where(foe > 0)
        rej = raw["rejected_by_photometry"].astype(str).str.lower().eq("true")
        vrej = raw[f"variability_flag_{band.lower()}_reject"].astype(str).str.lower().eq("true")
        flag = np.where(rej, "rejected_by_photometry", np.where(vrej, "rejected_by_variability", ""))
        parts.append(pd.DataFrame(dict(t_mjd=raw[tcol].astype(float) + GAIA_T0_MJD, mag=mag, err=err.fillna(0.05),
                                       band=band, survey="GAIA", flag=flag,
                                       camera=raw["transit_id"].astype(str))))
    return series.normalize(pd.concat(parts, ignore_index=True))


def lightcurve(source_id: int) -> tuple[pd.DataFrame, Provenance]:
    prov = Provenance(archive="ESA Gaia DR3 epoch photometry (datalink)", query={"source_id": int(source_id)})
    got = fetch([source_id])
    df = got.get(int(source_id), series.empty())
    prov.rows_raw = len(df)
    prov.rows_kept = int((df.flag == "").sum()) if len(df) else 0
    if df.empty:
        prov.status = "empty"
        prov.notes.append("no Gaia DR3 epoch photometry (only published for sources Gaia flagged as variable)")
    else:
        prov.notes.append("variability_flag rejections are kept but flagged; Gaia flagged them as outliers, "
                          "which for a real dip can mean the dip itself")
    return df, prov
