"""AAVSO International Database: a century of amateur observers, many with research-grade CCDs.

For several famous dusty stars the best-sampled optical light curve was made by amateurs.
Oddsky credits them by observer code in every series it builds.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import series
from .http import request
from .provenance import Provenance

VSX = "https://www.aavso.org/vsx/index.php"
JD_TO_MJD = 2400000.5
# Bands worth analysing. Visual estimates ("Vis.", ~0.1-0.3 mag precision) are the century-long
# backbone of the AAVSO record and are kept as their own series, never mixed with CCD bands.
GOOD_BANDS = {"V", "B", "R", "I", "CV", "TG", "TB", "TR", "SG", "SR", "SI", "CR", "Vis."}


def vsx_object(name: str) -> dict | None:
    r = request("GET", VSX, params={"view": "api.object", "ident": name, "format": "json"}, timeout=60)
    try:
        obj = r.json().get("VSXObject")
    except ValueError:
        return None
    return obj or None


def _parse(text: str) -> pd.DataFrame:
    """Pipe-delimited, except that observers' free-text comments may themselves contain pipes."""
    lines = text.splitlines()
    header = lines[0].split("|")
    n, ci = len(header), header.index("comment")
    rows = []
    for line in lines[1:]:
        f = line.split("|")
        if len(f) > n:
            extra = len(f) - n
            f = f[:ci] + ["|".join(f[ci:ci + extra + 1])] + f[ci + extra + 1:]
        if len(f) == n:
            rows.append(f)
    return pd.DataFrame(rows, columns=header)


def lightcurve(name: str) -> tuple[pd.DataFrame, Provenance]:
    params = {"view": "api.delim", "ident": name, "delimiter": "|"}
    r = request("GET", VSX, params=params, timeout=180)
    prov = Provenance(archive="AAVSO International Database (VSX api.delim)", query=params)
    text = r.text.strip()
    if not text or "|" not in text.splitlines()[0]:
        prov.status = "empty"
        return series.empty(), prov
    raw = _parse(text)
    prov.rows_raw = len(raw)
    mag = pd.to_numeric(raw["mag"].str.replace("<", "", regex=False), errors="coerce")
    err = pd.to_numeric(raw.get("uncert"), errors="coerce")
    flag = np.where(raw.get("fainterThan", "0").astype(str) == "1", "upper_limit", "")
    flag = np.where(raw.get("val", "").astype(str) == "T", "discrepant", flag)
    band = raw["band"].fillna("?").str.strip()
    flag = np.where((flag == "") & ~band.isin(GOOD_BANDS), "other_band", flag)
    df = pd.DataFrame(dict(
        t_mjd=pd.to_numeric(raw["JD"], errors="coerce") - JD_TO_MJD,
        mag=mag, err=err.fillna(0.1), band=band, survey="AAVSO", flag=flag,
        observer=raw.get("by", "").fillna(""),
    ))
    df = series.normalize(df)
    prov.rows_kept = int((df.flag == "").sum())
    counts = df[df.flag == ""].observer.value_counts()
    prov.notes.append("observers (good points): " + ", ".join(f"{k}:{v}" for k, v in counts.head(12).items()))
    prov.notes.append("upper limits, discrepant (val=T) and non-standard bands are kept but flagged; "
                      "visual estimates form their own series 'Vis.'")
    return df, prov
