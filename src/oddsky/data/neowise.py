"""NEOWISE-R (2013-12 to 2024-07): the infrared heartbeat, one visit every ~6 months.

Single exposures are noisy and full of artifacts. Oddsky applies the standard cuts, then
collapses each ~1-day visit into a robust mean. Every cut is recorded in provenance.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from astropy.io import ascii as aascii

from . import series
from .http import request
from .provenance import Provenance

GATOR = "https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query"
COLS = (
    "mjd,w1mpro,w1sigmpro,w2mpro,w2sigmpro,qual_frame,qi_fact,saa_sep,moon_masked,cc_flags,"
    "ph_qual,w1sat,w2sat,nb,na,w1snr,w2snr,w1rchi2,w2rchi2"
)
# Profile-fit photometry saturates around these magnitudes (Vega).
SATURATION = {"W1": 8.0, "W2": 7.0}
VISIT_GAP_DAYS = 30.0


def fetch_exposures(ra: float, dec: float, radius_arcsec: float = 3.0) -> tuple[pd.DataFrame, Provenance]:
    params = dict(catalog="neowiser_p1bs_psd", spatial="cone", radius=radius_arcsec, radunits="arcsec",
                  objstr=f"{ra} {dec}", outfmt=1, selcols=COLS)
    r = request("GET", GATOR, params=params, timeout=300)
    prov = Provenance(archive="IRSA Gator neowiser_p1bs_psd", query=params)
    if "[struct stat=\"ERROR\"" in r.text:
        prov.status = "unavailable"
        prov.notes.append(r.text.strip().splitlines()[-1][:300])
        return pd.DataFrame(), prov
    tbl = aascii.read(r.text.splitlines(), format="ipac")
    df = tbl.to_pandas()
    prov.rows_raw = len(df)
    if df.empty:
        prov.status = "empty"
    return df, prov


def quality_cuts(df: pd.DataFrame, band: str, prov: Provenance) -> pd.DataFrame:
    """Standard single-exposure cuts (Cutri et al. explanatory supplement; Hwang & Zakamska 2020)."""
    b = band.lower()
    idx = 0 if b == "w1" else 1
    cuts = [
        ("qual_frame > 0", df["qual_frame"] > 0),
        ("qi_fact > 0", df["qi_fact"] > 0),
        ("saa_sep > 0", df["saa_sep"] > 0),
        ("moon_masked == '00'", df["moon_masked"].astype(str).str.zfill(2) == "00"),
        (f"cc_flags[{idx}] == '0'", df["cc_flags"].astype(str).str.zfill(4).str[idx] == "0"),
        (f"ph_qual[{idx}] in (A,B)", df["ph_qual"].astype(str).str[idx].isin(["A", "B"])),
        ("nb == 1 (no blending)", df["nb"] == 1),
        (f"{b}snr >= 4", df[f"{b}snr"] >= 4),
        # Bright stars have high rchi2 everywhere (PSF mismatch); cut only this source's outliers.
        (f"{b}rchi2 < 5x source median", df[f"{b}rchi2"] < 5 * np.nanmedian(df[f"{b}rchi2"])),
        (f"{b}mpro finite", np.isfinite(df[f"{b}mpro"].astype(float))),
    ]
    mask = np.ones(len(df), bool)
    for label, m in cuts:
        m = np.asarray(m, bool)
        dropped = int((mask & ~m).sum())
        if dropped:
            prov.cuts.append(f"{band}: {label} removed {dropped}")
        mask &= m
    return df[mask]


def visits(df: pd.DataFrame, band: str) -> pd.DataFrame:
    """Group exposures into visits (gaps > 30 d) and take a clipped median per visit."""
    b = band.lower()
    if df.empty:
        return series.empty()
    t = df["mjd"].to_numpy(float)
    order = np.argsort(t)
    t = t[order]
    m = df[f"{b}mpro"].to_numpy(float)[order]
    e = df[f"{b}sigmpro"].to_numpy(float)[order]
    sat = df[f"{b}sat"].to_numpy(float)[order]
    group = np.concatenate([[0], np.cumsum(np.diff(t) > VISIT_GAP_DAYS)])
    rows = []
    for g in np.unique(group):
        sel = group == g
        mm, ee, tt = m[sel], e[sel], t[sel]
        med = np.median(mm)
        mad = 1.4826 * np.median(np.abs(mm - med)) if len(mm) > 1 else np.nan
        if np.isfinite(mad) and mad > 0:
            keep = np.abs(mm - med) < 4 * mad
            mm, ee, tt = mm[keep], ee[keep], tt[keep]
        n = len(mm)
        if n == 0:
            continue
        mean = float(np.median(mm))
        scatter = 1.4826 * np.median(np.abs(mm - mean)) if n > 2 else np.nanmedian(ee)
        err = float(max(scatter / np.sqrt(n), np.nanmedian(ee) / np.sqrt(n), 0.005))
        flags = []
        if n < 3:
            flags.append("few_exposures")
        if mean < SATURATION[band]:
            flags.append("saturated")
        if np.nanmax(sat[sel]) > 0.05:
            flags.append("saturated_pixels")
        rows.append(dict(t_mjd=float(np.median(tt)), mag=mean, err=err, band=band, survey="NEOWISE",
                         flag=",".join(flags), n_exp=n, scatter=float(scatter)))
    return series.normalize(pd.DataFrame(rows))


def lightcurve(ra: float, dec: float) -> tuple[pd.DataFrame, Provenance]:
    raw, prov = fetch_exposures(ra, dec)
    if raw.empty:
        return series.empty(), prov
    parts = []
    for band in ("W1", "W2"):
        cut = quality_cuts(raw, band, prov)
        parts.append(visits(cut, band))
    df = pd.concat(parts, ignore_index=True)
    prov.rows_kept = len(df)
    prov.notes.append("rows_kept counts 6-month visits (W1 and W2), not exposures")
    return series.normalize(df), prov
