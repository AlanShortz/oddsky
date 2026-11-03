"""AllWISE (2010-11) catalogue row for a target, and the H-0016 diagnostic for its profile-fit photometry.

H-0016 found that the AllWISE profile-fit magnitudes (w1mpro, w2mpro) of a few clean, isolated W1 = 11-14 stars are wrong by
0.4-1.7 mag in both bands while the aperture magnitudes (w1mag), 2MASS, the unWISE images and NEOWISE all agree. Every such
failure has an anomalously low profile-fit SNR for its magnitude, an aperture-minus-profile difference above 0.4 mag, and an
AllWISE position off Gaia by 0.35-2.6" (hunts/H-0016/README.md, section 4; referee report, finding 5). The catalogue columns
below are what the Skeptic needs to warn about it; nothing here calls the network except `catalog()`.
"""

from __future__ import annotations

import io

import numpy as np
import pandas as pd

from .http import request
from .provenance import Provenance

TAP = "https://irsa.ipac.caltech.edu/TAP/sync"
COLS = ("cntr, designation, ra, dec, sigra, sigdec, w1mpro, w1sigmpro, w1snr, w1rchi2, w1mag, w1sigm, w1nm, w1m, "
        "w2mpro, w2sigmpro, w2snr, w2rchi2, w2mag, w2sigm, w3mpro, w3sigmpro, w4mpro, w4sigmpro, nb, na, cc_flags, ext_flg, "
        "var_flg, ph_qual, pmra, pmdec, sigpmra, sigpmdec, w1mjdmean, j_m_2mass, h_m_2mass, k_m_2mass, r_2mass")
ALLWISE_EPOCH = 2010.5  # mean epoch of the 2010-11 frames, roughly; the catalogue has w1mjdmean per source

# Median profile-fit W1 SNR of clean AllWISE sources against W1 (3,069 sources in a 1.5-deg cone at |b| = 80, 2026-11-03,
# hunts/H-0016/reviews): flat at ~47.5 to W1 = 12.5 (a calibration floor caps the SNR), then 45.6 at 13.0, 44.0 at 13.5,
# 41.5 at 14.0, 38.9 at 14.5; quartiles are within +-1. Beyond 14.5 a linear extrapolation (-5 per mag) to 16.
_SNR_W1 = np.array([8.0, 12.5, 13.0, 13.5, 14.0, 14.5, 16.0])
_SNR_MED = np.array([47.5, 47.5, 45.6, 44.0, 41.5, 38.9, 31.4])


def expected_w1snr(w1: float) -> float:
    """Median AllWISE profile-fit W1 SNR of a clean source of this magnitude (8 <= W1 <= 16)."""
    return float(np.interp(w1, _SNR_W1, _SNR_MED))


def catalog(ra: float, dec: float, radius_arcsec: float = 3.0) -> tuple[dict | None, Provenance]:
    """The AllWISE source nearest to (ra, dec) within the radius, as a dict of catalogue columns, or None."""
    prov = Provenance(archive="IRSA AllWISE (allwise_p3as_psd)", query={"ra": ra, "dec": dec, "radius_arcsec": radius_arcsec})
    q = (f"SELECT {COLS} FROM allwise_p3as_psd WHERE CONTAINS(POINT('ICRS',ra,dec),"
         f"CIRCLE('ICRS',{ra},{dec},{radius_arcsec / 3600:.7f}))=1")
    try:
        r = request("POST", TAP, timeout=120, data={"QUERY": q, "FORMAT": "csv"})
    except Exception as e:  # noqa: BLE001
        prov.status = "unavailable"
        prov.notes.append(str(e)[:200])
        return None, prov
    text = r.text.strip()
    if not text or "\n" not in text:
        prov.status = "empty"
        return None, prov
    df = pd.read_csv(io.StringIO(text))
    prov.rows_raw = len(df)
    if df.empty:
        prov.status = "empty"
        return None, prov
    sep = 3600 * np.hypot((df.ra - ra) * np.cos(np.radians(dec)), df.dec - dec)
    row = df.iloc[int(np.argmin(sep))].to_dict()
    row["sep_arcsec"] = float(sep.min())
    row["n_within_radius"] = int(len(df))
    prov.rows_kept = 1
    return {k: (None if (isinstance(v, float) and np.isnan(v)) else (v.item() if hasattr(v, "item") else v))
            for k, v in row.items()}, prov


def diagnose(aw: dict, gaia: dict | None = None) -> dict:
    """Apply the H-0016 profile-fit diagnostic to an AllWISE row. Returns the three test values and a verdict:
    'ok', 'suspect' (one test fails) or 'bad' (two or more). Tests: aperture minus profile |w1mag - w1mpro| > 0.3;
    w1snr below half the expected SNR for the magnitude (8 <= W1 <= 16 only); detected in fewer than 60% of the W1 frames
    (w1nm / w1m; the catalogue-wide failure class sits at a median 0.47, real stars at 1.0); AllWISE position more than 0.35"
    from the Gaia DR3 position propagated to the AllWISE epoch (only when Gaia ra/dec are given and nb = 1)."""
    out: dict = {}
    w1, ap, snr = aw.get("w1mpro"), aw.get("w1mag"), aw.get("w1snr")
    if w1 is not None and (w1 < 8 or (aw.get("w1sat") or 0) > 0.05):
        # saturated in AllWISE: the profile fit and the aperture disagree for a known reason, and the H-0016 calibration
        # (8 <= W1 <= 14.5) does not apply
        return {"tests_failed": 0, "verdict": "saturated", "w1mpro": float(w1)}
    fails = 0
    if w1 is not None and ap is not None:
        out["aperture_minus_profile_w1"] = float(ap - w1)
        if abs(ap - w1) > 0.3:
            fails += 1
    if w1 is not None and snr is not None and 8 <= w1 <= 16:
        out["w1snr"], out["w1snr_expected"] = float(snr), expected_w1snr(w1)
        if snr < 0.5 * out["w1snr_expected"]:
            fails += 1
    if aw.get("w1nm") is not None and aw.get("w1m"):
        out["frame_detection_fraction"] = float(aw["w1nm"] / aw["w1m"])
        if out["frame_detection_fraction"] < 0.6:
            fails += 1
    if gaia and gaia.get("ra") is not None and gaia.get("dec") is not None and aw.get("ra") is not None and aw.get("nb", 1) == 1:
        dt = aw.get("w1mjdmean")
        yrs = ((dt - 51544.5) / 365.25 + 2000.0 - 2016.0) if dt else (ALLWISE_EPOCH - 2016.0)
        pmra, pmdec = gaia.get("pmra") or 0.0, gaia.get("pmdec") or 0.0
        gra = gaia["ra"] + yrs * pmra / 3.6e6 / np.cos(np.radians(gaia["dec"]))
        gdec = gaia["dec"] + yrs * pmdec / 3.6e6
        off = 3600 * float(np.hypot((aw["ra"] - gra) * np.cos(np.radians(gdec)), aw["dec"] - gdec))
        out["offset_from_gaia_arcsec"] = off
        if off > 0.35:
            fails += 1
    out["tests_failed"] = fails
    out["verdict"] = "ok" if fails == 0 else ("suspect" if fails == 1 else "bad")
    return out
