"""r9: frame-level scrutiny of the two 'single-night spikes' (J191120, J075219). For every night with a >5 sigma excess:
unit, band, number of frames, number of distinct detector positions (x,y clusters > 50 px apart), frame-to-frame flux scatter
vs the formal error, PSF major axis vs that unit's median in the same season, mag5sig and sky vs the season median.
An artifact (ghost, satellite, cosmic ray, bad frame) lives in one frame or one pointing; a real source is in every frame,
at every detector position, in every unit that looked, and on adjacent nights."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import atlas_raw, mjd2date  # noqa: E402

for k, (t0, base_sel) in {"J191120": (59293.6, (59500, 61500)), "J075219": (58207.3, (58700, 61500))}.items():
    r = atlas_raw(k)
    r = r[(r.err == 0) & (r.dujy > 0)]
    print(f"== {k}")
    rows = []
    for (F, cam), d in r.groupby(["F", "cam"]):
        b = d[(d.mjd > base_sel[0]) & (d.mjd < base_sel[1])]
        if len(b) < 20:
            b = d[np.abs(d.mjd - t0) > 400]
        if len(b) < 10:
            continue
        bmed, brob = np.median(b.ujy), 1.4826 * np.median(np.abs(b.ujy - np.median(b.ujy)))
        season = d[np.abs(d.mjd - t0) < 120]
        mmaj, mm5, msky = season.maj.median(), season.mag5sig.median(), season.sky.median()
        for night, n in season.groupby("night"):
            exc = np.median(n.ujy) - bmed
            if exc < 5 * brob / np.sqrt(len(n)) or exc < 3 * np.median(n.dujy):
                continue
            xy = n[["x", "y"]].values
            clusters = []
            for p in xy:
                if not any(np.hypot(*(p - q)) < 50 for q in clusters):
                    clusters.append(p)
            sc = np.std(n.ujy, ddof=1) if len(n) > 1 else np.nan
            rows.append((mjd2date(n.mjd.mean()), round(n.mjd.mean() - t0, 1), F, cam, len(n), len(clusters), int(np.median(n.ujy)),
                         int(bmed), int(exc), round(sc / np.median(n.dujy), 1) if len(n) > 1 else np.nan,
                         round(n.maj.median() - mmaj, 2), round(n.mag5sig.median() - mm5, 2), round(n.sky.median() - msky, 2),
                         round(n.chi_n.median(), 1)))
    df = pd.DataFrame(rows, columns=["date", "dt", "F", "unit", "nfr", "npos", "med_ujy", "base", "excess", "scat/err",
                                     "dmaj", "dm5", "dsky", "chiN"]).sort_values("dt")
    print(df.to_string(index=False))
    print(f"  nights with >5 sigma excess: {len(df)}; units: {sorted(df.unit.unique())}; bands: {sorted(df.F.unique())}; "
          f"span {df.dt.min()} to {df.dt.max()} d")
