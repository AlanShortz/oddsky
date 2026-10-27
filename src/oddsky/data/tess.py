"""TESS: 27-day sectors at minutes cadence. Superb for short structure, and the richest
source of instrumental artifacts in the sky, which is exactly why the Skeptic loves it."""

from __future__ import annotations

import contextlib
import io
import logging
import warnings

import numpy as np
import pandas as pd

from ..paths import cache_dir
from . import series
from .provenance import Provenance

log = logging.getLogger("oddsky")

# lightkurve TessQualityFlags bits
DESAT = 32          # reaction-wheel desaturation (momentum dump)
SCATTERED = 2048 | 4096
AUTHORS = ("SPOC", "TESS-SPOC", "QLP")
BIN_DAYS = 10 / 1440  # 10-minute bins keep every astrophysical timescale we care about and the repo small


def bin_cadence(df: pd.DataFrame, width: float) -> pd.DataFrame:
    if df.empty:
        return df
    key = np.floor(df["t_mjd"].to_numpy() / width)
    df = df.assign(_k=key, _bad=(df["flag"] != "").astype(int))
    g = df.groupby(["camera", "_bad", "_k"], sort=False)
    out = g.agg(t_mjd=("t_mjd", "median"), mag=("mag", "median"), err=("err", "median"),
                quality=("quality", lambda q: int(np.bitwise_or.reduce(q.to_numpy()))), n=("mag", "size")).reset_index()
    out["err"] = out["err"] / np.sqrt(out["n"])
    out["flag"] = np.where(out["_bad"] == 1, "quality", "")
    out["band"], out["survey"] = "TESS", "TESS"
    return out.drop(columns=["_k", "_bad"])


def lightcurve(ra: float, dec: float, max_sectors: int = 8) -> tuple[pd.DataFrame, Provenance, dict]:
    """Returns (series, provenance, meta). meta holds per-sector CROWDSAP and momentum-dump times."""
    prov = Provenance(archive="MAST TESS light curves via lightkurve", query={"ra": ra, "dec": dec, "authors": AUTHORS})
    meta: dict = {"sectors": {}}
    try:
        import lightkurve as lk
    except ImportError:
        prov.status = "unavailable"
        prov.notes.append("install oddsky[tess] for TESS light curves")
        return series.empty(), prov, meta
    with warnings.catch_warnings(), contextlib.redirect_stdout(io.StringIO()):
        warnings.simplefilter("ignore")
        try:
            res = lk.search_lightcurve(f"{ra} {dec}", radius=10, author=AUTHORS)
        except Exception as e:  # noqa: BLE001
            prov.status = "unavailable"
            prov.notes.append(f"MAST search failed: {e}"[:300])
            return series.empty(), prov, meta
        if len(res) == 0:
            prov.status = "empty"
            return series.empty(), prov, meta
        # One light curve per sector, preferring SPOC 120 s, then TESS-SPOC, then QLP.
        tab = res.table.to_pandas()
        tab["rank"] = tab["author"].map({a: i for i, a in enumerate(AUTHORS)}).fillna(9)
        tab["sector"] = tab["mission"].str.extract(r"(\d+)").astype(float)
        tab["idx"] = np.arange(len(tab))
        pick = tab.sort_values(["sector", "rank", "exptime"]).groupby("sector").head(1).head(max_sectors)
        parts = []
        dl = cache_dir() / "lightkurve"
        for _, row in pick.iterrows():
            try:
                lc = res[int(row["idx"])].download(download_dir=str(dl), quality_bitmask="none")
            except Exception as e:  # noqa: BLE001
                prov.notes.append(f"sector {int(row['sector'])} download failed: {e}"[:200])
                continue
            sector = int(lc.meta.get("SECTOR", row["sector"]))
            q = np.asarray(lc.quality.value if hasattr(lc.quality, "value") else lc.quality, dtype=int)
            col = "pdcsap_flux" if "pdcsap_flux" in lc.columns else "flux"
            f = np.asarray(lc[col].value, float)
            fe = np.asarray(lc[col + "_err"].value if col + "_err" in lc.columns else lc.flux_err.value, float)
            t = np.asarray(lc.time.value, float) + 2457000.0 - 2400000.5  # BTJD -> MJD
            ok = np.isfinite(f) & (f > 0)
            med = np.nanmedian(f[ok & (q == 0)]) if (ok & (q == 0)).any() else np.nanmedian(f[ok])
            mag = -2.5 * np.log10(np.where(ok, f, np.nan) / med)
            err = 1.0857 * fe / np.where(ok, f, np.nan)
            flag = np.where(q & ~(1024 | 64) != 0, "quality", "")
            parts.append(pd.DataFrame(dict(t_mjd=t, mag=mag, err=err, band="TESS", survey="TESS",
                                           flag=flag, camera=f"S{sector}", quality=q)))
            meta["sectors"][sector] = dict(
                author=str(row["author"]), exptime=float(row["exptime"]),
                crowdsap=_f(lc.meta.get("CROWDSAP")), flfrcsap=_f(lc.meta.get("FLFRCSAP")),
                t_start=float(np.nanmin(t)), t_end=float(np.nanmax(t)),
                desat_mjd=[float(x) for x in t[(q & DESAT) != 0]],
                flux_column=col, relative="delta-mag vs sector median",
            )
    if not parts:
        prov.status = "unavailable"
        return series.empty(), prov, meta
    raw_n = sum(len(x) for x in parts)
    df = series.normalize(bin_cadence(pd.concat(parts, ignore_index=True), BIN_DAYS))
    prov.rows_raw = raw_n
    prov.cuts.append(f"binned to {BIN_DAYS * 1440:.0f}-min medians per sector (good and flagged cadences kept apart)")
    prov.rows_kept = int((df.flag == "").sum())
    prov.notes.append("TESS magnitudes are relative (delta-mag vs each sector's median); sectors: "
                      + ", ".join(str(s) for s in sorted(meta["sectors"])))
    return df, prov, meta


def _f(x):
    try:
        x = float(x)
        return x if np.isfinite(x) else None
    except (TypeError, ValueError):
        return None
