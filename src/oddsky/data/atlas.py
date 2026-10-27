"""ATLAS forced photometry (fallingstar-data.com): the whole sky every night or two since 2015.

Four 0.5 m telescopes (Hawaii x2, Chile, South Africa), two broad filters, cyan (c, ~420-650 nm)
and orange (o, ~560-820 nm), AB magnitudes, 5-sigma depth o ~ 19.5. Forced PSF photometry at any
position on either the reduced image (what a variable star needs) or the difference image.

The server is public but needs a free account; the API token is read from ATLAS_TOKEN or fetched
once from ATLAS_USER / ATLAS_PASSWORD and cached under the Oddsky cache directory. Without any of
those every call returns an empty series with status "unavailable", never an exception.

Citations the server asks for: Tonry et al. 2018 (survey), Heinze et al. 2018 (variable stars),
Smith et al. 2020 (transients), Shingles et al. 2021 (this service).
"""

from __future__ import annotations

import io
import json
import logging
import os
import time

import httpx
import numpy as np
import pandas as pd

from ..paths import cache_dir
from . import series
from .http import UA
from .provenance import Provenance

log = logging.getLogger("oddsky")

API = "https://fallingstar-data.com/forcedphot"
AB_ZERO_UJY = 23.9  # m_AB = 23.9 - 2.5 log10(flux / uJy)
SNR_MIN = 3.0
RADIUS_ARCSEC = 8.0  # ATLAS pixels are 1.86"; the forced PSF collects light from this far out
MJD_MIN_DEFAULT = 57200.0  # mid-2015, first ATLAS data


# ----------------------------------------------------------------------------- credentials
def token() -> str | None:
    if t := os.environ.get("ATLAS_TOKEN"):
        return t.strip()
    cache = cache_dir() / "atlas" / "token"
    if cache.exists():
        return cache.read_text().strip() or None
    user, pw = os.environ.get("ATLAS_USER"), os.environ.get("ATLAS_PASSWORD")
    if not (user and pw):
        return None
    r = httpx.post(f"{API}/api-token-auth/", data={"username": user, "password": pw}, timeout=60,
                   headers={"User-Agent": UA})
    if r.status_code != 200:
        log.warning("ATLAS token request failed: %s %s", r.status_code, r.text[:200])
        return None
    t = r.json().get("token")
    if t:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(t)
        cache.chmod(0o600)
    return t


def available() -> bool:
    return token() is not None


def _headers() -> dict:
    return {"Authorization": f"Token {token()}", "Accept": "application/json", "User-Agent": UA}


# ----------------------------------------------------------------------------- the queue
def submit(ra: float, dec: float, mjd_min: float = MJD_MIN_DEFAULT, mjd_max: float | None = None,
           use_reduced: bool = True, max_wait_s: float = 900) -> str:
    """Queue one forced-photometry task; returns the task URL. Honours 429 Retry-After."""
    data = {"ra": ra, "dec": dec, "mjd_min": mjd_min, "send_email": False, "use_reduced": use_reduced}
    if mjd_max is not None:
        data["mjd_max"] = mjd_max
    waited = 0.0
    while True:
        r = httpx.post(f"{API}/queue/", headers=_headers(), data=data, timeout=120)
        if r.status_code == 201:
            return r.json()["url"]
        if r.status_code == 429:
            wait = float(r.headers.get("Retry-After", 30))
            waited += wait
            if waited > max_wait_s:
                raise RuntimeError("ATLAS queue: rate-limited for too long")
            log.info("ATLAS queue full; retry in %.0fs", wait)
            time.sleep(wait)
            continue
        raise RuntimeError(f"ATLAS queue: {r.status_code} {r.text[:200]}")


def status(task_url: str) -> dict:
    r = httpx.get(task_url, headers=_headers(), timeout=120)
    r.raise_for_status()
    return r.json()


def wait(task_url: str, poll_s: float = 15.0, max_wait_s: float = 3600) -> str:
    """Block until the task finishes; returns the result URL."""
    t0 = time.time()
    while True:
        st = status(task_url)
        if st.get("finishtimestamp"):
            if not st.get("result_url"):
                raise RuntimeError(f"ATLAS task finished without a result: {json.dumps(st)[:200]}")
            return st["result_url"]
        if time.time() - t0 > max_wait_s:
            raise TimeoutError(f"ATLAS task {task_url} not finished after {max_wait_s:.0f}s")
        time.sleep(poll_s)


def download(result_url: str) -> str:
    r = httpx.get(result_url, headers=_headers(), timeout=300)
    r.raise_for_status()
    return r.text


# ----------------------------------------------------------------------------- parsing
RAW_COLUMNS = ["mjd", "m", "dm", "ujy", "dujy", "F", "err", "chi_n", "ra", "dec", "x", "y", "maj", "min",
               "phi", "apfit", "mag5sig", "sky", "obs"]


def parse(text: str) -> pd.DataFrame:
    """The server's whitespace table: `###MJD m dm uJy duJy F err chi/N RA Dec x y maj min phi apfit mag5sig Sky Obs`."""
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    if not lines:
        return pd.DataFrame(columns=RAW_COLUMNS)
    df = pd.read_csv(io.StringIO("\n".join(lines)), sep=r"\s+", header=None, names=RAW_COLUMNS, engine="python")
    for c in RAW_COLUMNS:
        if c not in ("F", "obs"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def flux_to_mag(ujy, dujy, snr_min: float = SNR_MIN):
    """AB magnitude from a forced flux. Below `snr_min` the point becomes a 5-sigma upper limit.

    Returns (mag, err, flag) arrays; limits carry mag = 5-sigma limit, err = NaN, flag "upper_limit".
    Negative or zero fluxes never raise: they are limits too.
    """
    f = np.asarray(ujy, float)
    df_ = np.asarray(dujy, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        snr = np.where(df_ > 0, f / df_, np.nan)
        det = np.isfinite(snr) & (snr >= snr_min) & (f > 0)
        mag = np.where(det, AB_ZERO_UJY - 2.5 * np.log10(np.where(f > 0, f, np.nan)), np.nan)
        err = np.where(det, 1.0857 / snr, np.nan)
        lim = AB_ZERO_UJY - 2.5 * np.log10(np.where(df_ > 0, 5.0 * df_, np.nan))
        mag = np.where(det, mag, lim)
    flag = np.where(det, "", "upper_limit").astype(object)
    bad = ~np.isfinite(mag)
    flag[bad] = "atlas_bad"
    return mag, err, flag


def to_series(raw: pd.DataFrame, chi_max: float = 10.0) -> pd.DataFrame:
    if raw.empty:
        return series.empty()
    mag, err, flag = flux_to_mag(raw["ujy"], raw["dujy"])
    bad = (raw["err"].fillna(0) != 0) | (raw["chi_n"] > chi_max) | ~raw["F"].isin(["c", "o"])
    # ATLAS saturates near 12th magnitude: a "detection" brighter than 9, or a 5-sigma limit brighter than
    # 10 (a flux error above ~1e5 uJy), is a bad frame, not a star
    junk = (np.asarray(mag) < 9.0) | ((flag == "upper_limit") & (np.asarray(mag) < 10.0))
    flag = np.where(bad.to_numpy() | junk, "atlas_bad", flag)
    df = pd.DataFrame(dict(
        t_mjd=raw["mjd"], mag=mag, err=err, band="ATLAS_" + raw["F"].astype(str), survey="ATLAS", flag=flag,
        camera=raw["obs"].astype(str).str[:3],  # 01a Haleakala, 02a Mauna Loa, 03a El Sauce, 04a Sutherland
        flux_ujy=raw["ujy"], dflux_ujy=raw["dujy"],
    ))
    df["err"] = df["err"].fillna(0.0)  # series.normalize keeps NaN err; limits are flagged anyway
    return series.normalize(df)


def nightly_bins(df: pd.DataFrame) -> pd.DataFrame:
    """Inverse-variance mean in flux space per night and band, then back to magnitudes.

    Works on the output of `to_series` (needs flux_ujy/dflux_ujy). Limits are combined too, so
    four 30 s exposures on one night reach deeper than any one of them.
    """
    d = df[df.flag.isin(["", "upper_limit"])].copy()
    if d.empty:
        return series.empty()
    d["_night"] = np.floor(d["t_mjd"] + 0.5)
    w = 1.0 / d["dflux_ujy"].clip(lower=1e-3) ** 2
    d["_w"], d["_wf"] = w, w * d["flux_ujy"]
    g = d.groupby(["_night", "band"])
    out = pd.DataFrame({
        "t_mjd": g["t_mjd"].mean(),
        "flux_ujy": g["_wf"].sum() / g["_w"].sum(),
        "dflux_ujy": 1.0 / np.sqrt(g["_w"].sum()),
        "n_exp": g.size(),
        "camera": g["camera"].first(),
    }).reset_index()
    mag, err, flag = flux_to_mag(out["flux_ujy"], out["dflux_ujy"])
    out["mag"], out["err"], out["flag"], out["survey"] = mag, np.nan_to_num(err), flag, "ATLAS"
    return series.normalize(out.drop(columns=["_night"]))


# ----------------------------------------------------------------------------- the public call
def lightcurve(ra: float, dec: float, mjd_min: float = MJD_MIN_DEFAULT, use_reduced: bool = True,
               nightly: bool = False, poll_s: float = 15.0, max_wait_s: float = 3600,
               raw_cache: str | None = None) -> tuple[pd.DataFrame, Provenance]:
    """Submit, wait, download, convert. `raw_cache` names a file to reuse / save the server text."""
    params = {"ra": ra, "dec": dec, "mjd_min": mjd_min, "use_reduced": use_reduced, "nightly": nightly}
    prov = Provenance(archive="ATLAS forced photometry (fallingstar-data.com), reduced images", query=params)
    text = None
    if raw_cache and os.path.exists(raw_cache):
        text = open(raw_cache).read()
        prov.notes.append(f"reused cached server response {raw_cache}")
    elif not available():
        prov.status = "unavailable"
        prov.notes.append("no ATLAS credentials (set ATLAS_TOKEN, or ATLAS_USER and ATLAS_PASSWORD)")
        return series.empty(), prov
    else:
        try:
            task = submit(ra, dec, mjd_min=mjd_min, use_reduced=use_reduced)
            prov.query["task"] = task
            text = download(wait(task, poll_s=poll_s, max_wait_s=max_wait_s))
        except Exception as e:  # noqa: BLE001
            prov.status = "unavailable"
            prov.notes.append(f"ATLAS request failed: {str(e)[:160]}")
            return series.empty(), prov
        if raw_cache:
            os.makedirs(os.path.dirname(raw_cache) or ".", exist_ok=True)
            open(raw_cache, "w").write(text)
    raw = parse(text)
    prov.rows_raw = int(len(raw))
    if raw.empty:
        prov.status = "empty"
        return series.empty(), prov
    df = to_series(raw)
    n_bad = int((df.flag == "atlas_bad").sum())
    n_lim = int((df.flag == "upper_limit").sum())
    prov.cuts.append(f"ATLAS: err flag / chi2 per dof > 10 / unknown filter / brighter than saturation flagged {n_bad}")
    prov.cuts.append(f"ATLAS: SNR < {SNR_MIN:.0f} kept as 5-sigma upper limits {n_lim}")
    if nightly:
        df = nightly_bins(df)
        prov.notes.append("nightly inverse-variance bins in flux space")
    prov.rows_kept = int((df.flag == "").sum())
    sites = df[df.flag == ""].camera.value_counts().to_dict() if "camera" in df else {}
    prov.notes.append("telescopes (good points): " + ", ".join(f"{k}:{v}" for k, v in sites.items()))
    prov.notes.append("reduced-image PSF photometry: blends within ~8\" are included in the flux")
    return df, prov
