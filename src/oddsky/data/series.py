"""The one shape every light curve takes inside Oddsky.

Columns: t_mjd, mag, err, band, survey, flag (empty string = good), plus optional extras
(camera, observer, n_exp). Magnitudes everywhere; TESS flux becomes delta-mag.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

COLUMNS = ["t_mjd", "mag", "err", "band", "survey", "flag"]


def empty() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="float64" if c in ("t_mjd", "mag", "err") else "object") for c in COLUMNS})


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    for c in COLUMNS:
        if c not in df:
            df[c] = "" if c == "flag" else np.nan
    df["flag"] = df["flag"].fillna("").astype(str)
    df = df[np.isfinite(df["t_mjd"]) & np.isfinite(df["mag"])]
    return df.sort_values("t_mjd").reset_index(drop=True)


def good(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["flag"] == ""]
