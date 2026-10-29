"""Gaia epoch photometry: per-transit G, BP and RP. DR3 (2014-07 to 2017-05) published it for ~10 million variables;
DR4 (scheduled December 2026; 2014-07 to 2020-01) publishes it for every source. `fetch` asks for DR4 first and falls
back to DR3, so predictions sealed against DR4-era windows (e.g. OS-0016) grade themselves once DR4 is out. The DR4
request uses the DR3 parameters with RELEASE="Gaia DR4"; if the archive names it differently, the DR3 fallback keeps
everything working as before.

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


RELEASES = ("Gaia DR4", "Gaia DR3")


def fetch(source_ids: list[int], chunk: int = 50, releases: tuple[str, ...] = RELEASES) -> dict[int, pd.DataFrame]:
    """Epoch photometry for many sources at once (the server takes at most 50 ids per request), from the newest
    release that answers. Sources without epoch photometry are simply absent."""
    out: dict[int, pd.DataFrame] = {}
    ids_all = [int(s) for s in source_ids]
    for rel in releases:
        todo = [s for s in ids_all if s not in out]
        if not todo:
            break
        try:
            out.update(_fetch_release(todo, chunk, rel))
        except Exception:  # noqa: BLE001  an unreleased or renamed release must not break the older one
            if rel == releases[-1]:
                raise
    return out


def _fetch_release(source_ids: list[int], chunk: int, release: str) -> dict[int, pd.DataFrame]:
    out: dict[int, pd.DataFrame] = {}
    for i in range(0, len(source_ids), chunk):
        ids = ",".join(str(int(s)) for s in source_ids[i:i + chunk])
        # One try for a release that may not exist yet; the usual retries for the one we know is there.
        r = request("POST", DATALINK, timeout=300, retries=1 if release != RELEASES[-1] else 3, data=dict(
            RETRIEVAL_TYPE="EPOCH_PHOTOMETRY", ID=ids, FORMAT="csv", DATA_STRUCTURE="DATAMODEL_STANDARD",
            RELEASE=release, VALID_DATA="false"))
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
    df = series.normalize(pd.concat(parts, ignore_index=True))
    return df


def lightcurve(source_id: int) -> tuple[pd.DataFrame, Provenance]:
    prov = Provenance(archive="ESA Gaia epoch photometry (datalink; DR4 if published, else DR3)", query={"source_id": int(source_id)})
    got = fetch([source_id])
    df = got.get(int(source_id), series.empty())
    prov.rows_raw = len(df)
    prov.rows_kept = int((df.flag == "").sum()) if len(df) else 0
    if df.empty:
        prov.status = "empty"
        prov.notes.append("no Gaia epoch photometry (DR3 published it only for sources Gaia flagged as variable)")
    else:
        prov.notes.append("variability_flag rejections are kept but flagged; Gaia flagged them as outliers, "
                          "which for a real dip can mean the dip itself")
    return df, prov
