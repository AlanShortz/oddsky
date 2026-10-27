from __future__ import annotations

import json
from collections.abc import Callable

import numpy as np
import pandas as pd

from .. import __version__
from ..analysis.excursions import excursions
from ..analysis.periodogram import periodogram
from ..case.model import now
from ..case.store import CaseStore, _jsonable

# Effective blending radii (arcsec): roughly the PSF FWHM or photometric aperture.
RADII = {"NEOWISE": 6.1, "ASAS-SN": 16.0, "TESS": 42.0, "ZTF": 2.0, "AAVSO": 5.0}

Check = dict


def _check(cid: str, title: str, status: str, finding: str, **numbers) -> Check:
    return {"id": cid, "title": title, "status": status, "finding": finding, "numbers": numbers}


def blending(store: CaseStore) -> list[Check]:
    ctx = store.context()
    nbs = ctx.get("neighbors")
    if nbs is None:
        return [_check("blend", "Neighbours inside the beam", "skip", "no Gaia neighbour table")]
    target_bprp = (ctx.get("gaia") or {}).get("bp_rp") or 1.0
    out = []
    have = {s.upper() for s in store.surveys()}
    for survey, r in RADII.items():
        if survey.replace("-", "").upper() not in {h.replace("-", "") for h in have}:
            continue
        inside = [n for n in nbs if n["sep_arcsec"] <= r]
        worst = max(inside, key=lambda n: n["flux_ratio_G"], default=None)
        # Red neighbours are brighter in the infrared than G suggests.
        red = [n for n in inside if (n.get("bp_rp") or 0) > target_bprp + 1.0 and n["dG"] < 4] if survey == "NEOWISE" else []
        if worst is None:
            out.append(_check(f"blend_{survey.lower()}", f"Neighbours inside the {survey} beam ({r}\")", "pass",
                              f"no Gaia source within {r}\"", radius_arcsec=r))
            continue
        frac = sum(n["flux_ratio_G"] for n in inside)
        status = "fail" if worst["flux_ratio_G"] >= 0.5 else "warn" if (worst["flux_ratio_G"] >= 0.1 or red) else "pass"
        msg = (f"{len(inside)} Gaia source(s) within {r}\"; brightest contributes {worst['flux_ratio_G']:.1%} of the "
               f"target's G flux at {worst['sep_arcsec']:.1f}\"")
        if red:
            msg += f"; {len(red)} is much redder than the target and may matter more in the infrared"
        if status == "fail":
            msg += ". A variable neighbour could produce this signal."
        out.append(_check(f"blend_{survey.lower()}", f"Neighbours inside the {survey} beam ({r}\")", status, msg,
                          radius_arcsec=r, n_inside=len(inside), total_flux_ratio_G=round(frac, 4),
                          brightest_flux_ratio=round(worst["flux_ratio_G"], 4), brightest_sep=worst["sep_arcsec"]))
    tess = ctx.get("tess", {}).get("sectors", {})
    crowd = [v.get("crowdsap") for v in tess.values() if v.get("crowdsap")]
    if crowd:
        c = min(crowd)
        status = "fail" if c < 0.7 else "warn" if c < 0.9 else "pass"
        out.append(_check("tess_crowdsap", "TESS aperture contamination (CROWDSAP)", status,
                          f"worst sector: {c:.2f} of aperture flux is from the target", min_crowdsap=c))
    return out


def neowise_quality(store: CaseStore) -> list[Check]:
    if "neowise" not in store.surveys():
        return []
    df = store.series("neowise")
    prov = store.provenance().get("neowise", {})
    sat = df["flag"].str.contains("saturat").sum()
    few = df["flag"].str.contains("few_exposures").sum()
    out = []
    status = "fail" if sat > len(df) / 2 else "warn" if sat else "pass"
    out.append(_check("wise_saturation", "WISE saturation", status,
                      f"{sat} of {len(df)} visits are at or brighter than saturation (W1<8, W2<7)"
                      if sat else "all visits fainter than the W1/W2 saturation limits",
                      saturated_visits=int(sat)))
    raw = prov.get("rows_raw") or 0
    removed = {}
    for c in prov.get("cuts", []):
        band, rest = c.split(":", 1)
        removed[band] = removed.get(band, 0) + int(rest.rsplit(" ", 1)[-1])
    worst = max(removed.values(), default=0)
    status = "warn" if raw and worst / raw > 0.5 else "pass"
    out.append(_check("wise_cuts", "NEOWISE single-exposure quality cuts", status,
                      f"{raw} exposures; cuts removed up to {worst} ({worst / raw:.0%}) per band; "
                      f"{few} visits kept with fewer than 3 exposures" if raw else "no exposures",
                      exposures=raw, removed_per_band=removed, thin_visits=int(few)))
    return out


def independent_confirmation(store: CaseStore) -> list[Check]:
    """Has anyone else seen it? The most important question in astronomy."""
    out = []
    optical = [s for s in store.surveys() if s in ("aavso", "asassn", "ztf", "tess")]
    if not [o for o in optical if o != "tess"]:
        return [_check("confirmation", "Independent optical confirmation", "warn",
                       "the only optical data are TESS: one spacecraft, normalised per sector. Nothing here has "
                       "been seen by a second instrument.")]
    sources = {}
    for s in optical:
        df = store.series(s)
        df = df[df.flag == ""]
        if s == "aavso" and "observer" in df:
            for obs, n in df.observer.value_counts().items():
                sources[f"AAVSO observer {obs}"] = int(n)
        elif "camera" in df and s != "tess":
            sources[s.upper()] = int(len(df))
        else:
            sources[s.upper()] = int(len(df))
    # TESS is normalised per sector, so it can confirm shape and timing but not absolute brightness.
    big = {k: v for k, v in sources.items() if v >= 20 and k != "TESS"}
    status = "pass" if len(big) >= 2 else "warn"
    top = sorted(big.items(), key=lambda kv: -kv[1])
    finding = (f"optical data from {len(big)} independent source(s): " + ", ".join(f"{k} ({v})" for k, v in top[:5])
               + (f", and {len(top) - 5} more" if len(top) > 5 else ""))
    if status == "warn":
        finding += ". One instrument or observer is a single point of failure; seek a second."
    if "TESS" in sources:
        finding += (" TESS is not counted: it is normalised per sector, so it confirms an event only if a sector "
                    "overlaps it, and never its absolute depth.")
    out.append(_check("confirmation", "Independent optical confirmation", status, finding, sources=sources))
    return out


def chromaticity(store: CaseStore) -> list[Check]:
    """Do the bands agree on what happened? Dust dims every band in a physical ratio; artifacts rarely do."""
    from ..analysis.color import EXTINCTION_RATIO, cross_band

    if "aavso" not in store.surveys():
        return []
    df = store.series("aavso")
    df = df[df.flag == ""]
    bands = [b for b in ("B", "R", "I") if (df.band == b).sum() > 50]
    v = df[df.band == "V"]
    if len(v) < 50 or not bands or np.ptp(np.percentile(v.mag, [2, 98])) < 0.2:
        return [_check("chromatic", "Colour of the variability", "skip",
                       "needs CCD V plus another band, and > 0.2 mag of V variability")]
    slopes, rs = {}, {}
    for b in bands:
        cb = cross_band(df[df.band == b], v, b, "V", tol_days=0.5)
        if "slope_dA_dB" in cb:
            slopes[b], rs[b] = round(cb["slope_dA_dB"], 3), round(cb["pearson_r"], 3)
    if not slopes:
        return []
    ism = {b: round(EXTINCTION_RATIO[b] / EXTINCTION_RATIO["V"], 2) for b in slopes}
    coherent = all(r > 0.7 for r in rs.values())
    status = "pass" if coherent else "warn"
    text = ", ".join(f"d{b}/dV = {slopes[b]:.2f} (ISM dust {ism[b]}, r = {rs[b]:.2f})" for b in slopes)
    note = (" All bands move together, as real dimming or brightening must." if coherent else
            " At least one band does not track V: suspect calibration, a blend, or a band-specific artifact.")
    return [_check("chromatic", "Colour of the variability (all simultaneous AAVSO data)", status, text + "." + note,
                   slopes=slopes, pearson_r=rs, ism=ism)]


def aliases(store: CaseStore) -> list[Check]:
    out = []
    for s in store.surveys():
        df = store.series(s)
        df = df[df.flag == ""]
        if df.empty:
            continue
        band = df.band.value_counts().index[0]
        g = df[df.band == band]
        if len(g) >= 30:
            span = g.t_mjd.max() - g.t_mjd.min()
            pg = periodogram(g, min_period=0.5 if s != "neowise" else 200, max_period=span / 2, n_peaks=3, samples=8000)
            if "peaks" not in pg:
                continue
            top = pg["peaks"][0]
            if s in ("aavso", "asassn", "ztf") and any("day" in f for f in top["alias_flags"]):
                # Nightly sampling: the day alias dominates. Report the best period longer than 2 d too.
                longer = periodogram(g, min_period=2.0, max_period=span / 2, n_peaks=3, samples=8000)["peaks"][0]
                top = {**top, "alias_flags": top["alias_flags"] + [
                    f"best period above 2 d: {longer['period_days']:.1f} d"
                    + (f" ({'; '.join(longer['alias_flags'])})" if longer["alias_flags"] else "")]}
            status = "warn" if top["alias_flags"] else "pass"
            out.append(_check(f"alias_{s}_{band}", f"Periodicity vs survey rhythms ({s.upper()} {band})", status,
                              f"strongest period {top['period_days']:.2f} d"
                              + (f" coincides with: {'; '.join(top['alias_flags'])}" if top["alias_flags"] else
                                 " is not a known survey/Earth rhythm (not yet evidence it is real)"),
                              top_period_days=top["period_days"], power=top["power"]))
    return out[:6]


def onset_coverage(store: CaseStore) -> list[Check]:
    out = []
    for s in ("aavso", "asassn", "ztf"):
        if s not in store.surveys():
            continue
        df = store.series(s)
        df = df[df.flag == ""]
        for band, g in df.groupby("band"):
            if len(g) < 30:
                continue
            # Coarse on purpose: only dips deeper than 0.1 mag against a 600-day baseline, the three deepest.
            ex = excursions(g, baseline_days=600, min_depth=0.1)
            evs = [e for e in ex.get("events", []) if e["direction"] == "fainter"][:3]
            for e in evs:
                if e["starts_after_gap"]:
                    out.append(_check(f"onset_{s}_{band}", f"Was the start seen? ({s.upper()} {band})", "warn",
                                      f"the {e['depth_mag']:.2f}-mag dip peaking at MJD {e['peak_mjd']:.0f} begins at the "
                                      "edge of the data or right after a gap; its true start and shape are unobserved",
                                      event=e))
                    break
            else:
                if evs:
                    out.append(_check(f"onset_{s}_{band}", f"Was the start seen? ({s.upper()} {band})", "pass",
                                      f"the {len(evs)} deepest dip(s) (> 0.1 mag vs a 600-day baseline) all have an observed ingress",
                                      n_events=len(evs)))
    return out[:4]


def tess_systematics(store: CaseStore) -> list[Check]:
    if "tess" not in store.surveys():
        return []
    ctx = store.context().get("tess", {}).get("sectors", {})
    df = store.series("tess")
    out = []
    for sector, g in df[df.flag == ""].groupby("camera"):
        meta = ctx.get(str(sector).lstrip("S"), {}) if ctx else {}
        ex = excursions(g, baseline_days=3.0, k_sigma=5, min_depth=0.003, bin_days=0.02, max_gap_days=0.3)
        evs = [e for e in ex.get("events", []) if e["direction"] == "fainter"]
        if not evs:
            continue
        desat = np.array(meta.get("desat_mjd", []))
        t0, t1 = g.t_mjd.min(), g.t_mjd.max()
        bad = []
        for e in evs:
            near_dump = desat.size and np.any(np.abs(desat - e["peak_mjd"]) < 0.3)
            near_edge = min(e["peak_mjd"] - t0, t1 - e["peak_mjd"]) < 1.0
            gaps = np.diff(g.t_mjd.to_numpy())
            mid_gap = g.t_mjd.to_numpy()[:-1][gaps > 0.5]
            near_orbit_gap = mid_gap.size and np.any(np.abs(mid_gap - e["peak_mjd"]) < 1.0)
            if near_dump or near_edge or near_orbit_gap:
                bad.append(e)
        status = "fail" if bad and len(bad) == len(evs) else "warn" if bad else "pass"
        out.append(_check(f"tess_sys_{sector}", f"TESS dips vs spacecraft events ({sector})", status,
                          f"{len(evs)} dip(s); {len(bad)} sit within 0.3 d of a momentum dump or 1 d of a sector/orbit edge",
                          n_dips=len(evs), n_suspect=len(bad)))
    return out[:6]


def gaia_baseline(store: CaseStore) -> list[Check]:
    """Gaia's 2014-2017 mean brightness is a free pre-event baseline. Did the series start mid-event?"""
    g = store.context().get("gaia") or {}
    if g.get("G") is None or g.get("bp_rp") is None:
        return []
    c = g["bp_rp"]
    # Gaia DR3 photometric transformation (Riello et al. 2021), valid for -0.5 < BP-RP < 2.75.
    v_pred = g["G"] - (-0.02704 + 0.01424 * c - 0.2156 * c**2 + 0.01426 * c**3)
    out = []
    for s in ("aavso", "asassn"):
        if s not in store.surveys():
            continue
        df = store.series(s)
        v = df[(df.flag == "") & (df.band == "V")]
        if len(v) < 10:
            continue
        first = v[v.t_mjd < v.t_mjd.min() + 60].mag.median()
        delta = float(first - v_pred)
        status = "warn" if abs(delta) > 0.2 else "pass"
        out.append(_check(f"baseline_{s}", f"Does {s.upper()} start at the star's normal brightness?", status,
                          f"first 60 days of V: median {first:.2f}; Gaia DR3 (2014-17 mean) implies V = {v_pred:.2f}; "
                          f"difference {delta:+.2f} mag"
                          + (". The series begins mid-event: its own median is not the star's normal state."
                             if status == "warn" else ""),
                          v_first=round(float(first), 3), v_gaia=round(float(v_pred), 3), delta=round(delta, 3)))
    return out


def astrometry(store: CaseStore) -> list[Check]:
    g = store.context().get("gaia")
    if not g:
        return []
    ruwe = g.get("ruwe")
    if ruwe is None:
        return []
    status = "warn" if ruwe > 1.4 else "pass"
    return [_check("ruwe", "Gaia astrometric wobble (RUWE)", status,
                   f"RUWE = {ruwe:.2f}" + (" > 1.4: likely an unresolved companion, or a photocentre shifted by variability"
                                            if status == "warn" else " (single-star-like astrometry)"), ruwe=ruwe)]


BATTERY: list[Callable[[CaseStore], list[Check]]] = [
    blending, neowise_quality, independent_confirmation, gaia_baseline, chromaticity, onset_coverage, aliases, tess_systematics,
    astrometry,
]


def run(store: CaseStore, write: bool = True) -> dict:
    checks: list[Check] = []
    for fn in BATTERY:
        try:
            checks.extend(fn(store))
        except Exception as e:  # noqa: BLE001 - a broken check must say so, not hide
            checks.append(_check(fn.__name__, fn.__name__, "skip", f"check crashed: {type(e).__name__}: {e}"))
    counts = {k: sum(c["status"] == k for c in checks) for k in ("fail", "warn", "pass", "skip")}
    report = {
        "generated_at": now(),
        "oddsky_version": __version__,
        "summary": f"{counts['fail']} fail, {counts['warn']} warn, {counts['pass']} pass, {counts['skip']} skipped",
        "counts": counts,
        "checks": checks,
    }
    report = json.loads(json.dumps(report, default=_jsonable))
    if write:
        (store.path / "skeptic.json").write_text(json.dumps(report, indent=2))
    return report


def as_frame(report: dict) -> pd.DataFrame:
    return pd.DataFrame(report["checks"])[["status", "title", "finding"]]
