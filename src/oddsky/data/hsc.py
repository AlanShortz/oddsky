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


class Truncated(RuntimeError):
    """A query still returns a full page after its right-ascension slice has been cut down to nothing."""


def _get(table: str, params: dict) -> pd.DataFrame:
    r = request("GET", f"{API}/{table}/magaper2.csv", params={**params, "pagesize": PAGE, "page": 1}, timeout=600.0, retries=4)
    return pd.read_csv(io.StringIO(r.text)) if r.text.strip() else pd.DataFrame()


def _pages(table: str, params: dict, ra_lo: float, ra_hi: float, pause: float = 0.2, depth: int = 0) -> pd.DataFrame:
    """Every row of one query, without the service's paging.

    The service's `page` parameter is not safe: it has no stable order (`sort_by` is ignored), so consecutive pages
    overlap and rows fall between them. Asking for IC 2574's 98,000 summary rows in two pages returned 87,245 distinct
    sources; H-0019's first runs lost about a quarter of every catalogue longer than one page this way, and the loss
    was found by `oddsky.analysis.twiceseen` (hunts/H-0020). Instead each request is one page, and a full page means the
    right-ascension slice [ra_lo, ra_hi) is halved and asked again.
    """
    df = _get(table, {**params, "MatchRA.gte": ra_lo, "MatchRA.lt": ra_hi})
    if len(df) < PAGE:
        return df
    if ra_hi - ra_lo < 1e-6 or depth > 40:
        raise Truncated(f"{table}: {PAGE} rows in RA [{ra_lo}, {ra_hi})")
    mid = (ra_lo + ra_hi) / 2
    time.sleep(pause)
    left = _pages(table, params, ra_lo, mid, pause, depth + 1)
    time.sleep(pause)
    right = _pages(table, params, mid, ra_hi, pause, depth + 1)
    return pd.concat([left, right], ignore_index=True)


def _ra_span(ra: float, dec: float, radius_deg: float) -> tuple[float, float]:
    half = radius_deg / max(np.cos(np.radians(min(abs(dec) + radius_deg, 89.9))), 1e-3) * 1.01 + 1e-4
    return ra - half, ra + half


def summary(ra: float, dec: float, radius_deg: float, columns: list[str] | None = None, **filters) -> pd.DataFrame:
    """Summary rows in a cone. `filters` are passed to the service as written, e.g. `**{"A_F814W_N.gte": 2}`."""
    params: dict = {"ra": ra, "dec": dec, "radius": radius_deg, **filters}
    if columns:
        params["columns"] = "[" + ",".join(dict.fromkeys([*columns, "MatchID", "MatchRA"])) + "]"
    df = _pages("summary", params, *_ra_span(ra, dec, radius_deg))
    return df.drop_duplicates("MatchID", ignore_index=True) if len(df) else df


def visits(ra: float, dec: float, radius_deg: float, filt: str, detector: str | None = None, mag_max: float | None = None,
           columns: tuple[str, ...] = VISIT_COLS) -> pd.DataFrame:
    """One row per detection in `filt` inside the cone (the detailed table), optionally for one detector and brighter
    than `mag_max` (MagAper2, AB)."""
    params: dict = {"ra": ra, "dec": dec, "radius": radius_deg, "Filter": filt,
                    "columns": "[" + ",".join(dict.fromkeys([*columns, "MatchID", "SourceID", "ImageID", "MatchRA"])) + "]"}
    if detector:
        params["Detector"] = detector
    if mag_max is not None:
        params["MagAper2.lt"] = mag_max
    df = _pages("detailed", params, *_ra_span(ra, dec, radius_deg))
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
