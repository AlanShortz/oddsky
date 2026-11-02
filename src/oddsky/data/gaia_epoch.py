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
    return fetch_report(source_ids, chunk, releases)[0]


def fetch_report(source_ids: list[int], chunk: int = 50,
                 releases: tuple[str, ...] = RELEASES) -> tuple[dict[int, pd.DataFrame], dict]:
    """`fetch`, plus a report of what happened: for each release tried, whether it answered, how many sources it returned
    and the error if it failed; and which release each source came from. A failing DR4 request falls back to DR3 without
    raising, so the report is how a renamed release or a changed schema is noticed instead of silently waiting."""
    out: dict[int, pd.DataFrame] = {}
    report: dict = {"releases": [], "source_release": {}}
    ids_all = [int(s) for s in source_ids]
    for rel in releases:
        todo = [s for s in ids_all if s not in out]
        if not todo:
            break
        try:
            got = _fetch_release(todo, chunk, rel)
        except Exception as e:  # noqa: BLE001  an unreleased or renamed release must not break the older one
            report["releases"].append({"release": rel, "ok": False, "n": 0, "error": f"{type(e).__name__}: {str(e)[:200]}"})
            if rel == releases[-1]:
                raise
            continue
        report["releases"].append({"release": rel, "ok": True, "n": len(got), "error": ""})
        out.update(got)
        report["source_release"].update({sid: rel for sid in got})
    return out, report


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


# Column names per band: (time, magnitude, flux_over_error). DR3 prefixes G with "g_transit_"; the DR4 draft data model
# (2026-06-26) drops "transit_" (g_obs_time, g_mag, g_flux_over_error) and keeps the BP/RP names. DR4's epoch_photometry has
# no rejected_by_photometry or variability_flag_*_reject columns: rejected BP/RP values are empty (NaN) and variability
# rejections moved to a separate DataLink product (EPOCH_FLAGS_VARI). Without those columns no transit is flagged here, and
# non-finite magnitudes are dropped by series.normalize, as they always were. (dr4_ensemble.md section 2.5 item 2.)
COLUMN_MAPS = {
    "dr3": {"G": ("g_transit_time", "g_transit_mag", "g_transit_flux_over_error"),
            "BP": ("bp_obs_time", "bp_mag", "bp_flux_over_error"), "RP": ("rp_obs_time", "rp_mag", "rp_flux_over_error")},
    "dr4": {"G": ("g_obs_time", "g_mag", "g_flux_over_error"),
            "BP": ("bp_obs_time", "bp_mag", "bp_flux_over_error"), "RP": ("rp_obs_time", "rp_mag", "rp_flux_over_error")},
}


def column_map(raw: pd.DataFrame) -> tuple[str, dict]:
    """Which layout a raw epoch-photometry table uses. Raises KeyError naming the missing columns if neither fits."""
    cols = set(raw.columns)
    for name, m in COLUMN_MAPS.items():
        need = {c for v in m.values() for c in v} | {"transit_id"}
        if need <= cols:
            return name, m
    need = {c for v in COLUMN_MAPS["dr3"].values() for c in v} | {"transit_id"}
    raise KeyError(f"unknown epoch-photometry layout; missing {sorted(need - cols)}; have {sorted(cols)}")


def to_series(raw: pd.DataFrame) -> pd.DataFrame:
    _, cmap = column_map(raw)
    no = pd.Series(False, index=raw.index)
    parts = []
    for band in ("G", "BP", "RP"):
        tcol, mcol, ecol = cmap[band]
        mag = raw[mcol].astype(float)
        foe = raw[ecol].astype(float)
        err = 1.0857 / foe.where(foe > 0)
        rej = raw["rejected_by_photometry"].astype(str).str.lower().eq("true") if "rejected_by_photometry" in raw else no
        vcol = f"variability_flag_{band.lower()}_reject"
        vrej = raw[vcol].astype(str).str.lower().eq("true") if vcol in raw else no
        flag = np.where(rej, "rejected_by_photometry", np.where(vrej, "rejected_by_variability", ""))
        parts.append(pd.DataFrame(dict(t_mjd=raw[tcol].astype(float) + GAIA_T0_MJD, mag=mag, err=err.fillna(0.05),
                                       band=band, survey="GAIA", flag=flag,
                                       camera=raw["transit_id"].astype(str))))
    df = series.normalize(pd.concat(parts, ignore_index=True))
    return df


def lightcurve(source_id: int) -> tuple[pd.DataFrame, Provenance]:
    prov = Provenance(archive="ESA Gaia epoch photometry (datalink; DR4 if published, else DR3)", query={"source_id": int(source_id)})
    got, report = fetch_report([source_id])
    df = got.get(int(source_id), series.empty())
    used = report["source_release"].get(int(source_id))
    prov.query["release_used"] = used
    for r in report["releases"]:
        if not r["ok"]:
            prov.notes.append(f"{r['release']} request failed ({r['error']}); fell back to the next release")
    prov.rows_raw = len(df)
    prov.rows_kept = int((df.flag == "").sum()) if len(df) else 0
    if df.empty:
        prov.status = "empty"
        prov.notes.append("no Gaia epoch photometry (DR3 published it only for sources Gaia flagged as variable)")
    else:
        prov.notes.append(f"epoch photometry from {used}")
        prov.notes.append("variability_flag rejections are kept but flagged; Gaia flagged them as outliers, "
                          "which for a real dip can mean the dip itself")
    return df, prov
