"""Shared loaders for this review (written from scratch; does not import the investigators' scripts)."""
import os
import numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def ztf(k, cat0=True, nightly=True):
    z = pd.read_csv(f"{D}/ztf_{k}.csv")
    if cat0:
        z = z[z.catflags == 0]
    z = z[z.mag.notna()].copy()
    z["band"] = z.filtercode.str[-1]
    z["series"] = "ZTF_" + z.band + "_" + z.field.astype(str)
    if nightly:
        z["night"] = np.floor(z.mjd - 0.3)
        z["f"] = 10 ** (-0.4 * z.mag)
        g = z.groupby(["series", "band", "night"])
        out = g.agg(mjd=("mjd", "mean"), f=("f", "mean"), n=("f", "size"), e=("magerr", "median")).reset_index()
        out["mag"] = -2.5 * np.log10(out.f)
        out["magerr"] = np.sqrt(out.e ** 2 / out.n + 0.01 ** 2)
        z = out
    return z

def neowise(k):
    n = pd.read_csv(f"{D}/neowise_{k}.csv")
    return n

def to_ratio(df, mag="mag", err="magerr", series="series", base_mask=None):
    """Flux relative to each series' baseline median (base_mask: rows that define the baseline)."""
    df = df.copy()
    bm = base_mask if base_mask is not None else np.ones(len(df), bool)
    med = df[bm].groupby(series)[mag].median()
    df["fr"] = 10 ** (-0.4 * (df[mag] - df[series].map(med)))
    df["fe"] = df.fr * df[err] / 1.0857
    return df
