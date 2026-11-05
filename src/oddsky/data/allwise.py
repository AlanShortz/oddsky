"""AllWISE (2010-11) catalogue row for a target, and the H-0016 diagnostic for its profile-fit photometry.

H-0016 found that the AllWISE profile-fit magnitudes (w1mpro, w2mpro) of a few clean, isolated W1 = 11-14 stars are wrong by
0.4-1.7 mag in both bands while the aperture magnitudes (w1mag), 2MASS, the unWISE images and NEOWISE all agree. Every such
failure has an anomalously low profile-fit SNR for its magnitude, an aperture-minus-profile difference above 0.4 mag, and an
AllWISE position off Gaia by 0.35-2.6" (hunts/H-0016/README.md, section 4; referee report, finding 5). The catalogue columns
below are what the Skeptic needs to warn about it.

For some of them the AllWISE Reject Table (allwise_p3as_psr) holds a second extraction of the same star from the same Atlas
Tile, 0.5-2.3" away, at full SNR and with the right magnitude, marked `use_src = 0`: a duplicate not selected for the Catalog
(section 4d). `reject_entries()` fetches the Reject entries around a position and `best_duplicate()` picks that extraction.

Nothing here calls the network except `catalog()` and `reject_entries()`.
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
REJECT_COLS = ("designation, ra, dec, cntr, coadd_id, w1mpro, w1snr, w1mag, w2mpro, w2snr, w1nm, w1m, nb, cc_flags, rel, "
               "use_src, best_use_cntr")
# Read as text: cntr and best_use_cntr are 19-digit integers (a float corrupts them, and best_use_cntr can be null, which
# makes pandas read the column as float); cc_flags is a four-character code ("0000" must not become 0).
_REJECT_STR = ("designation", "cntr", "coadd_id", "cc_flags", "rel", "best_use_cntr")
# A clean duplicate (H-0016 section 4d: the 19 found had w1snr 44.5-49.0 at 0.46-2.25", all with use_src = 0)
DUP_MAX_SEP_ARCSEC = 3.0
DUP_MIN_W1SNR = 25.0
DUP_MIN_SNR_RATIO = 3.0
DUP_MIN_FRAME_FRACTION = 0.9

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


def reject_entries(ra: float, dec: float, radius_arcsec: float = 3.0) -> tuple[list[dict], Provenance]:
    """The AllWISE Reject Table entries within the radius of (ra, dec), nearest first, each with `sep_arcsec`. The
    identifiers (cntr, best_use_cntr) are strings. `prov.status` is 'ok' (entries returned), 'empty' (IRSA answered and
    there are none) or 'unavailable' (the query failed or the answer was not the table): an empty list with 'unavailable'
    says nothing about whether an entry exists."""
    prov = Provenance(archive="IRSA AllWISE Reject Table (allwise_p3as_psr)",
                      query={"ra": ra, "dec": dec, "radius_arcsec": radius_arcsec})
    q = (f"SELECT {REJECT_COLS} FROM allwise_p3as_psr WHERE CONTAINS(POINT('ICRS',ra,dec),"
         f"CIRCLE('ICRS',{ra},{dec},{radius_arcsec / 3600:.7f}))=1")
    try:
        r = request("POST", TAP, retries=2, timeout=300, data={"QUERY": q, "FORMAT": "csv"})
        text = r.text.strip()
        if not text.startswith("designation"):
            # IRSA can answer 200 with an error document; that is not "no entries"
            raise ValueError(f"not a CSV table: {text[:120]!r}")
        df = pd.read_csv(io.StringIO(text), dtype=dict.fromkeys(_REJECT_STR, str))
    except Exception as e:  # noqa: BLE001
        prov.status = "unavailable"
        prov.notes.append(str(e)[:200])
        return [], prov
    prov.rows_raw = len(df)
    if df.empty:
        prov.status = "empty"
        return [], prov
    df["sep_arcsec"] = 3600 * np.hypot((df.ra - ra) * np.cos(np.radians(dec)), df.dec - dec)
    df = df.sort_values("sep_arcsec")
    prov.rows_kept = len(df)
    return [{k: (None if pd.isna(v) else (v.item() if hasattr(v, "item") else v)) for k, v in row.items()}
            for row in df.to_dict(orient="records")], prov


def best_duplicate(aw: dict, rejects: list[dict]) -> dict | None:
    """The Reject Table entry that is a clean second extraction of the star behind the catalogue row `aw`, or None. No
    network. It must lie within 3", be a single-component fit (nb = 1), be a duplicate not selected for the Catalog
    (use_src = 0), have w1snr >= 25 and at least three times the catalogue entry's, and be detected in at least 90% of
    the W1 frames. Of several, one whose best_use_cntr is the catalogue entry's cntr comes first, then the nearest.
    `w1_correction` is what to add to the catalogue w1mpro to get the duplicate's."""
    cat_cntr = None if aw.get("cntr") is None else str(aw["cntr"])
    cat_snr = aw.get("w1snr") or 0.0
    good = []
    for e in rejects:
        sep, snr, w1, nm, m = e.get("sep_arcsec"), e.get("w1snr"), e.get("w1mpro"), e.get("w1nm"), e.get("w1m")
        if sep is None or snr is None or w1 is None or nm is None or not m:
            continue
        if (sep <= DUP_MAX_SEP_ARCSEC and e.get("nb") == 1 and e.get("use_src") == 0 and snr >= DUP_MIN_W1SNR
                and snr >= DUP_MIN_SNR_RATIO * cat_snr and nm / m >= DUP_MIN_FRAME_FRACTION):
            names = cat_cntr is not None and e.get("best_use_cntr") is not None and str(e["best_use_cntr"]) == cat_cntr
            good.append((not names, sep, e))
    if not good:
        return None
    not_named, _, e = min(good, key=lambda x: x[:2])
    return {"designation": e.get("designation"), "cntr": None if e.get("cntr") is None else str(e["cntr"]),
            "sep_arcsec": float(e["sep_arcsec"]), "w1mpro": float(e["w1mpro"]),
            "w2mpro": None if e.get("w2mpro") is None else float(e["w2mpro"]), "w1snr": float(e["w1snr"]),
            "w1mag": None if e.get("w1mag") is None else float(e["w1mag"]), "names_catalog_entry": not not_named,
            "w1_correction": None if aw.get("w1mpro") is None else float(e["w1mpro"] - aw["w1mpro"])}


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
