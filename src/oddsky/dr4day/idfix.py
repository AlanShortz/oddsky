"""Recover Gaia source ids that were written as floats (hunts/H-0004/*.csv: "4.756341994426711e+18").

A float64 keeps 53 bits, so a 19-digit id round-trips only to within half the float spacing (512 above 2^62, 256 below).
The true id is therefore inside a window of +-1024 around the float, and source_id is the archive's primary key, so one
`BETWEEN` per id is cheap. Of the ids in that window we keep the one at the catalogue position with the listed G.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

WINDOW = 1024


def window(float_id: str) -> tuple[int, int]:
    x = int(float(float_id))
    return x - WINDOW, x + WINDOW


def query(windows: list[tuple[int, int]], table: str = "gaiadr3.gaia_source") -> str:
    where = " OR ".join(f"(source_id BETWEEN {a} AND {b})" for a, b in windows)
    return f"SELECT source_id, ra, dec, phot_g_mean_mag FROM {table} WHERE {where}"


def match(cands: pd.DataFrame, rows: pd.DataFrame, max_sep_arcsec: float = 3.5, max_dg: float = 0.02) -> pd.DataFrame:
    """For each row (id, float_id, ra, dec, gaia_g) pick the candidate source inside its id window that sits within
    max_sep_arcsec and max_dg of the listed position and G. Unmatched rows keep an empty source_id and a reason.
    The positions may be WISE positions (H-0004 matched Gaia within 3"), so the position tolerance is loose; the listed G,
    to 0.02 mag, is what identifies the source."""
    out = []
    cid = cands.source_id.astype(str).map(int).to_numpy() if len(cands) else np.array([], dtype=np.int64)
    for r in rows.itertuples():
        rec = dict(id=r.id, float_id=r.float_id, ra=r.ra, dec=r.dec, gaia_g=r.gaia_g, pool=getattr(r, "pool", ""),
                   source_id="", sep_arcsec=np.nan, dG=np.nan, n_window=0, reason="")
        if not isinstance(r.float_id, str) or not r.float_id:
            rec["reason"] = "no Gaia id listed"
            out.append(rec)
            continue
        a, b = window(r.float_id)
        sel = cands[(cid >= a) & (cid <= b)]
        rec["n_window"] = len(sel)
        if sel.empty:
            rec["reason"] = "no source in the id window"
            out.append(rec)
            continue
        cosd = np.cos(np.radians(float(r.dec)))
        sep = 3600 * np.hypot((sel.ra.to_numpy(float) - float(r.ra)) * cosd, sel.dec.to_numpy(float) - float(r.dec))
        dg = np.abs(sel.phot_g_mean_mag.to_numpy(float) - float(r.gaia_g)) if np.isfinite(float(r.gaia_g)) else np.zeros(len(sel))
        ok = (sep <= max_sep_arcsec) & (dg <= max_dg)
        if ok.sum() == 0:
            j = int(np.argmin(sep))
            rec["reason"] = (f"no source in the window within {max_sep_arcsec}\" and {max_dg} mag "
                             f"(nearest {sep[j]:.1f}\", dG {dg[j]:.3f})")
        else:
            i = int(np.flatnonzero(ok)[np.argmin(sep[ok])])
            rec.update(source_id=str(sel.source_id.iloc[i]), sep_arcsec=round(float(sep[i]), 3), dG=round(float(dg[i]), 4),
                       reason="" if ok.sum() == 1 else f"{int(ok.sum())} sources matched; nearest kept")
        out.append(rec)
    return pd.DataFrame(out)


def recover(archive, rows: pd.DataFrame, per: int = 50, table: str = "gaiadr3.gaia_source") -> pd.DataFrame:
    """rows: id, float_id, ra, dec, gaia_g (and pool). Runs one small TAP job per `per` ids."""
    have = rows[rows.float_id.notna() & (rows.float_id != "")]
    parts = []
    for i in range(0, len(have), per):
        w = [window(x) for x in have.float_id.iloc[i:i + per]]
        parts.append(archive.tap(query(w, table)))
    cands = pd.concat([p for p in parts if len(p)], ignore_index=True) if parts else pd.DataFrame(
        columns=["source_id", "ra", "dec", "phot_g_mean_mag"])
    return match(cands, rows)
