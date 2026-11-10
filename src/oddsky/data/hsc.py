"""Hubble Source Catalog v3 (Whitmore+ 2016): every source Hubble's ACS, WFC3 and WFPC2 detected, visit by visit.

The catalogue is aperture photometry (SExtractor on Hubble Legacy Archive images) cross-matched between visits. Two tables
matter here: the summary (one row per matched source, `<Inst>_<Filter>` median magnitude, `_MAD` and `_N` measurements) and
the detailed table (one row per detection, with the image, time, instrument and concentration index).

Magnitudes are AB, in the small aperture ("MagAper2": 0.15" for ACS/WFC and WFC3/UVIS and IR, 0.30" for WFPC2), with no
aperture correction. Nothing here turns them into Vega or total magnitudes; H-0019 works in magnitudes relative to each
galaxy's own red-giant tip so that it never has to.

What the catalogue is not: it is not PSF photometry. In crowded fields a 0.15" aperture holds more than one star, and the
catalogue only keeps the visits the Hubble Legacy Archive combined (ACS/WFC3 to 2017, roughly). See hunts/H-0019.

`summary()` and `visits()` call the network; `pairs()` does not.
"""

from __future__ import annotations

import io
import time

import numpy as np
import pandas as pd

from .http import request

API = "https://catalogs.mast.stsci.edu/api/v0.1/hsc/v3"
PAGE = 50000
# Summary-table prefix of each detector, and the detector's name in the detailed table
PREFIX = {"ACS/WFC": "A", "WFC3/UVIS": "W3", "WFC3/IR": "W3", "WFPC2": "W2"}
VISIT_COLS = ("MatchID", "SourceID", "ImageID", "MatchRA", "MatchDec", "D", "StartMJD", "StopMJD", "ExposureTime",
              "Detector", "Filter", "MagAper2", "MagAuto", "CI", "Flags", "PropID", "XImage", "YImage", "ImageName")


def _pages(table: str, params: dict, max_rows: int | None = None, pause: float = 0.2) -> pd.DataFrame:
    """All pages of one query. The service has no stable default order, so rows are sorted by MatchID and duplicates
    across page boundaries are dropped by the caller's key."""
    frames, page = [], 1
    while True:
        r = request("GET", f"{API}/{table}/magaper2.csv", params={**params, "pagesize": PAGE, "page": page}, timeout=600.0,
                    retries=4)
        text = r.text
        if not text.strip():
            break
        df = pd.read_csv(io.StringIO(text))
        frames.append(df)
        if len(df) < PAGE or (max_rows and sum(len(f) for f in frames) >= max_rows):
            break
        page += 1
        time.sleep(pause)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def summary(ra: float, dec: float, radius_deg: float, columns: list[str] | None = None, **filters) -> pd.DataFrame:
    """Summary rows in a cone. `filters` are passed to the service as written, e.g. `**{"A_F814W_N.gte": 2}`."""
    params: dict = {"ra": ra, "dec": dec, "radius": radius_deg, "sort_by": "MatchID", **filters}
    if columns:
        params["columns"] = "[" + ",".join(columns) + "]"
    df = _pages("summary", params)
    return df.drop_duplicates("MatchID", ignore_index=True) if len(df) else df


def visits(ra: float, dec: float, radius_deg: float, filt: str, detector: str | None = None, mag_max: float | None = None,
           columns: tuple[str, ...] = VISIT_COLS) -> pd.DataFrame:
    """One row per detection in `filt` inside the cone (the detailed table), optionally for one detector and brighter
    than `mag_max` (MagAper2, AB)."""
    params: dict = {"ra": ra, "dec": dec, "radius": radius_deg, "Filter": filt, "sort_by": "MatchID",
                    "columns": "[" + ",".join(columns) + "]"}
    if detector:
        params["Detector"] = detector
    if mag_max is not None:
        params["MagAper2.lt"] = mag_max
    df = _pages("detailed", params)
    return df.drop_duplicates(["MatchID", "SourceID", "ImageID"], ignore_index=True) if len(df) else df


def pairs(det: pd.DataFrame, min_lag_days: float = 0.0) -> pd.DataFrame:
    """Every pair of visits of the same source with the same detector and filter.

    Detections in the same image (the catalogue sometimes splits one star in two) are averaged first. Returns one row per
    (MatchID, image pair): `mag` the mean of the two, `dmag` later minus earlier, `lag` in days, the two image ids, the
    larger concentration index and the OR of the flags.
    """
    if not len(det):
        return pd.DataFrame()
    d = (det.groupby(["MatchID", "Detector", "Filter", "ImageID"], as_index=False)
            .agg(mjd=("StartMJD", "mean"), mag=("MagAper2", "mean"), ci=("CI", "max"), flags=("Flags", "max"),
                 n=("MagAper2", "size"), ra=("MatchRA", "first"), dec=("MatchDec", "first"), prop=("PropID", "first")))
    d = d.sort_values(["MatchID", "Detector", "Filter", "mjd"])
    a = d.merge(d, on=["MatchID", "Detector", "Filter"], suffixes=("1", "2"))
    a = a[a.mjd2 > a.mjd1 + min_lag_days]
    out = pd.DataFrame({
        "MatchID": a.MatchID.values, "Detector": a.Detector.values, "Filter": a.Filter.values,
        "ra": a.ra1.values, "dec": a.dec1.values,
        "img1": a.ImageID1.values, "img2": a.ImageID2.values, "mjd1": a.mjd1.values, "mjd2": a.mjd2.values,
        "lag": (a.mjd2 - a.mjd1).values, "mag": ((a.mag1 + a.mag2) / 2).values, "mag1": a.mag1.values, "mag2": a.mag2.values,
        "dmag": (a.mag2 - a.mag1).values, "ci": np.maximum(a.ci1, a.ci2).values,
        "flags": np.maximum(a.flags1, a.flags2).values, "nsplit": np.maximum(a.n1, a.n2).values,
        "prop1": a.prop1.values, "prop2": a.prop2.values})
    return out.reset_index(drop=True)
