"""Release-day stage `astrolens` (hunt H-0015): Gaia DR4 epoch astrometry of Oddsky's ranked lens targets, fitted for an
astrometric microlensing deflection (theta_E, piE, lens mass) with `oddsky.analysis.astrolens`.

    targets   hunts/H-0015/data/ranked_targets.csv (sealed with the H-0015 forecast), Gaia DR3 ids mapped to the release by
              the pipeline's `idmap` stage (nearest within 0.5" and 0.3 mag; else the DR3 id as is)
    fetch     DataLink RETRIEVAL_TYPE=EPOCH_ASTROMETRY, `chunk` ids per request (50 anonymous), raw tables cached per source
              under <run>/epoch_astrometry/; a failed chunk is an error with its ids, never "no data"
    read      `normalise`: DR4's draft layout (one row per FoV transit, 10-element per-CCD arrays: index 0 = sky mapper,
              dropped; `used_by_agis_al` false dropped; |centroid_pos_al| > 1e6 mas dropped, a known DR4 issue) or a
              per-CCD long layout like the Gaia BH3 release; times are TCB ns since J2010.0 plus the barycentric correction
              -> MJD; CCDs are averaged per transit (weighted) with a 0.05 mas per-transit floor, as in the acceptance test
    photometry  the H-0014 epoch-photometry cache of the same run (G, BP, RP flux ratios to a quiet baseline) and, for the
              cases that have it, ATLAS from cases/<id>/data/atlas.parquet
    fit       `astrolens.fit_target`: deflection vs no deflection (both with blend-offset terms), the error rescaling and
              clipping of the acceptance test, theta_E upper limit, profile-likelihood mass interval
    output    <run>/astrolens/results.csv, summary.json; never a case, the ledger or a sealed file

With a release that has no epoch astrometry (`Release.has_epoch_astrometry` False: Gaia DR3), the stage says so
("epoch astrometry not available in dr3") and then runs every other step on simulated DR4-format tables built from the
targets' real scanning law (GOST, committed in hunts/H-0015/data/gost_transits.csv.gz): no lens for all but one positive
control. That is the dry run.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd

from ..analysis import astrolens as al

log = logging.getLogger("oddsky.dr4day")

H15 = Path("hunts/H-0015")
J2010_MJD = 55197.0          # J2010.0 (TCB) = JD 2455197.5
NS_PER_DAY = 86400e9
FLOOR_MAS = 0.05

# column names: DR4 draft data model (2026-06-26) first, then alternatives seen in the BH3 release / likely renames
ALIASES = {
    "time": ["obs_time_tcb", "observation_time_tcb", "obs_time", "transit_time_tcb"],
    "bary": ["obs_time_bary_corr", "barycentric_correction"],
    "w": ["centroid_pos_al", "w", "along_scan_position", "abscissa_al"],
    "sig": ["centroid_pos_error_al", "sigma_w", "w_error", "centroid_pos_al_error"],
    "theta": ["scan_pos_angle", "scan_angle", "psi"],
    "plx": ["parallax_factor_al", "parallax_factor"],
    "used": ["used_by_agis_al", "used", "outlier_flag"],
    "transit": ["transit_id"],
    "bjd": ["bjd_tcb", "time_bjd_tcb", "obs_time_bjd"],
}


def _col(df: pd.DataFrame, key: str):
    for c in ALIASES[key]:
        if c in df.columns:
            return c
    return None


def _arr(v) -> np.ndarray:
    """A per-CCD array cell: '[1.0, 2.0, ...]', '(1 2 ...)', '{...}', a list, or a scalar."""
    if isinstance(v, (list, tuple, np.ndarray)):
        return np.asarray(v, dtype=object)
    if isinstance(v, str):
        s = v.strip()
        if s[:1] in "[({" and s[-1:] in "])}":
            body = s[1:-1].strip()
            # comma-separated keeps empty cells (a null CCD, e.g. the sky mapper) in place; else whitespace-separated
            parts = [p.strip() for p in body.split(",")] if "," in body else body.split()
            return np.asarray([p if p.lower() not in ("", "null", "none", "nan") else "nan" for p in parts], dtype=object)
        return np.asarray([s], dtype=object)
    return np.asarray([v], dtype=object)


def _num(a) -> np.ndarray:
    return pd.to_numeric(pd.Series(a), errors="coerce").to_numpy(float)


def _bool(a) -> np.ndarray:
    s = pd.Series(a).astype(str).str.strip().str.lower()
    return s.isin(["true", "1", "t", "yes"]).to_numpy()


QUALITY = {  # carried through to the results for the referee (DR4 draft / pre-release sample names)
    "blended": ["blended"], "multipeak": ["multipeak"], "g_class": ["g_class", "window_class"], "gates": ["gates", "gate"],
    "proc_flags": ["transit_proc_flags", "ccd_proc_flags"], "excess_noise": ["agis_source_excess_noise"],
}
PLX_TOL = 0.02          # parallax_factor_al against fE sin(theta) + fN cos(theta) from the ephemeris (95th percentile)
SPAN_PAD_D = 5.0


def _qcol(df, key):
    for c in QUALITY[key]:
        if c in df.columns:
            return c
    return None


def _mode(vals):
    vals = [str(v) for v in vals if str(v).lower() not in ("", "nan", "none", "null")]
    if not vals:
        return ""
    u, c = np.unique(vals, return_counts=True)
    return str(u[np.argmax(c)])


class FormatError(ValueError):
    """The epoch astrometry does not pass a sanity check: the target is ineligible, never fitted silently."""


def normalise(raw: pd.DataFrame, per_transit: bool = True, theta_unit: str = "auto", ra: float | None = None,
              dec: float | None = None, span: tuple[float, float] | None = (al.DR4_START, al.DR4_END)) -> pd.DataFrame:
    """Raw epoch astrometry of one source -> one row per FoV transit (or per CCD): t_mjd (barycentric TCB), theta (rad),
    w (mas), sigma (mas), plx, n_ccd, and the quality columns present (frac_blended, frac_multipeak, wclass = the
    transit's window class, gates, frac_proc_flags; excess_noise per source).

    Sanity checks (each raises FormatError, so the target becomes ineligible instead of being fitted on misread data):
      * every time inside `span` +- 5 d (catches a wrong time unit or zero point);
      * `ra0`/`dec0` constant for the source;
      * with ra/dec given: `parallax_factor_al` equals fE sin(theta) + fN cos(theta) from the ephemeris to PLX_TOL. This
        settles the scan angle's unit, zero point and direction: theta_unit "auto" tries degrees (DR4's draft, BH3), then
        radians, and raises if neither matches.
    Raises ValueError (FormatError's parent) if a needed column is missing (a format change: add an alias)."""
    need = {k: _col(raw, k) for k in ("w", "sig", "theta", "plx")}
    missing = [k for k, v in need.items() if v is None]
    tcol, bcol, jcol = _col(raw, "time"), _col(raw, "bary"), _col(raw, "bjd")
    if missing or (tcol is None and jcol is None):
        raise ValueError(f"epoch astrometry columns not found: {missing + ([] if tcol or jcol else ['time'])}; "
                         f"have {list(raw.columns)[:40]}")
    for c in ("ra0", "dec0"):
        if c in raw.columns and len(raw):
            v = pd.to_numeric(raw[c], errors="coerce")
            if v.notna().any() and (v.max() - v.min()) > 1e-9:
                raise FormatError(f"{c} is not constant for the source (range {v.min()}..{v.max()})")
    ucol, trc = _col(raw, "used"), _col(raw, "transit")
    # a duplicated DataLink response: each transit (or, per-CCD layouts, each identical row) is used once
    raw = raw.drop_duplicates(subset=[trc]) if trc is not None and _col(raw, "time") is not None and raw[trc].is_unique is False \
        and str(raw[_col(raw, "time")].iloc[0]).startswith("[") else raw.drop_duplicates()
    qcols = {k: _qcol(raw, k) for k in QUALITY}
    rows = []
    for i, r in enumerate(raw.itertuples(index=False)):
        rd = r._asdict()
        w = _num(_arr(rd[need["w"]]))
        n = len(w)
        sig = _num(_arr(rd[need["sig"]]))
        th = _num(_arr(rd[need["theta"]]))
        if jcol is not None:
            t = _num(_arr(rd[jcol])) - 2400000.5
        else:
            t = J2010_MJD + _num(_arr(rd[tcol])) / NS_PER_DAY
            if bcol is not None:
                t = t + _num(_arr(rd[bcol]))[0] / NS_PER_DAY
        plx = _num(_arr(rd[need["plx"]]))
        used = np.ones(n, bool)
        if ucol is not None:
            u = _arr(rd[ucol])
            used = _bool(u) if ucol != "outlier_flag" else ~_bool(u)
        bc = lambda x, n=n: np.broadcast_to(x if len(x) == n else x[:1], (n,))  # noqa: E731
        sig, th, t, plx, used = bc(sig), bc(th), bc(t), bc(plx), bc(used)
        q = {}
        for k, c in qcols.items():
            if c is not None and k != "excess_noise":
                arr = _arr(rd[c])
                q[k] = np.broadcast_to(arr if len(arr) == n else arr[:1], (n,))
        idx = np.arange(n)
        keep = used & np.isfinite(w) & np.isfinite(sig) & (sig > 0) & np.isfinite(th) & np.isfinite(t) & (np.abs(w) < 1e6)
        if n == 10:                         # DR4 per-transit arrays: index 0 is the sky mapper (not used by AGIS)
            keep &= idx > 0
        transit = rd[trc] if trc is not None else i
        for j in np.flatnonzero(keep):
            rows.append(dict(transit=transit, t_mjd=t[j], theta_raw=th[j], w=w[j], sigma=sig[j], plx=plx[j],
                             **{k: v[j] for k, v in q.items()}))
    d = pd.DataFrame(rows)
    if d.empty:
        return pd.DataFrame(columns=["transit", "t_mjd", "theta", "w", "sigma", "plx", "n_ccd"])
    if span is not None:
        bad = (d.t_mjd < span[0] - SPAN_PAD_D) | (d.t_mjd > span[1] + SPAN_PAD_D)
        if bad.any():
            raise FormatError(f"{int(bad.sum())} of {len(d)} times outside the release span (MJD {d.t_mjd.min():.3f}.."
                              f"{d.t_mjd.max():.3f}): wrong time unit or zero point?")
    units = {"auto": ("deg", "rad"), "deg": ("deg",), "rad": ("rad",)}[theta_unit]
    chosen, devs = None, {}
    if ra is not None and dec is not None:
        fn, fe = al.parallax_factors(d.t_mjd.to_numpy(), ra, dec, scale=1.01)
        for un in units:
            th = np.radians(d.theta_raw) if un == "deg" else d.theta_raw
            devs[un] = float(np.percentile(np.abs(fe * np.sin(th) + fn * np.cos(th) - d.plx), 95))
            if devs[un] < PLX_TOL:
                chosen = un
                break
        if chosen is None:
            raise FormatError(f"parallax_factor_al does not match the scan angle for any unit/convention tried "
                              f"(95th-percentile deviation {devs}); scan-angle unit, zero point or direction differs")
    else:
        chosen = units[0]
    d["theta"] = np.radians(d.theta_raw) if chosen == "deg" else d.theta_raw
    d = d.drop(columns="theta_raw")
    d.attrs["theta_unit"] = chosen
    d.attrs["plx_deviation"] = devs.get(chosen)
    if qcols.get("excess_noise"):
        d.attrs["excess_noise"] = float(pd.to_numeric(raw[qcols["excess_noise"]], errors="coerce").median())
    if not per_transit:
        d["n_ccd"] = 1
        if "g_class" in d:
            d["wclass"] = d.g_class.astype(str)
        return d
    out = []
    for tr, g in d.groupby("transit", sort=False):
        wt = 1.0 / g.sigma.to_numpy() ** 2
        rec = dict(transit=tr, t_mjd=float(np.average(g.t_mjd, weights=wt)),
                   theta=float(np.arctan2(np.sum(wt * np.sin(g.theta)), np.sum(wt * np.cos(g.theta)))),
                   w=float(np.average(g.w, weights=wt)), sigma=float(np.sqrt(1.0 / wt.sum() + FLOOR_MAS**2)),
                   plx=float(np.average(g.plx, weights=wt)), n_ccd=len(g))
        if "blended" in g:
            rec["frac_blended"] = float(_bool(g.blended).mean())
        if "multipeak" in g:
            rec["frac_multipeak"] = float(_bool(g.multipeak).mean())
        if "g_class" in g:
            rec["wclass"] = _mode(g.g_class)
        if "gates" in g:
            rec["gates"] = _mode(g.gates)
        if "proc_flags" in g:
            rec["frac_proc_flags"] = float((pd.to_numeric(g.proc_flags, errors="coerce").fillna(0) != 0).mean())
        out.append(rec)
    o = pd.DataFrame(out).sort_values("t_mjd").reset_index(drop=True)
    o.attrs.update(d.attrs)
    return o


def quality_summary(ast: pd.DataFrame) -> dict:
    """Per-target summary of the carried quality columns (for the results table and the referee)."""
    q = {"theta_unit": ast.attrs.get("theta_unit", ""), "plx_factor_dev95": ast.attrs.get("plx_deviation"),
         "agis_source_excess_noise": ast.attrs.get("excess_noise")}
    for c in ("frac_blended", "frac_multipeak", "frac_proc_flags"):
        if c in ast:
            q[c] = float(ast[c].mean())
    for c in ("wclass", "gates"):
        if c in ast:
            v = ast[c].astype(str).value_counts()
            q[f"{c}_counts"] = ";".join(f"{k}:{n}" for k, n in v.items())
    return q


def simulated_raw(source_id: str, t, theta, plx, G: float, rng, q=None, theta_e: float = 0.0, fs: float = 1.0,
                  ra: float = 0.0, dec: float = 0.0) -> pd.DataFrame:
    """A DR4-draft-format epoch-astrometry table for one source (10-element per-CCD arrays as '[...]' strings), from
    forecast transits: per-CCD noise plus a per-transit common term, so that `normalise` gives back per-FoV errors."""
    t = np.asarray(t, float)
    sfov = al.sigma_al_fov(np.full(len(t), G))
    sccd = np.sqrt(np.maximum(sfov**2 - FLOOR_MAS**2, 1e-6)) * np.sqrt(9)
    w0 = np.zeros(len(t))
    if q is not None and theta_e > 0:
        from ..analysis.lensing import sun_offsets
        dn_s, de_s = sun_offsets(t, ra, dec, float(round(q[0])))
        tau = (t - q[0]) / q[1] + q[3] * dn_s + q[4] * de_s
        beta = q[2] + (-q[3] * de_s + q[4] * dn_s)
        un, ue = al.trajectory(tau, beta, q[3], q[4])
        dn, de = al.centroid_shift(un, ue, fs)
        w0 = theta_e * (de * np.sin(theta) + dn * np.cos(theta))
    dt = (t - al.J2017_5) / al.YEAR
    w0 = w0 + (-3.0 * dt * np.sin(theta) - 5.0 * dt * np.cos(theta)) + 0.2 * plx
    rows = []
    fmt = lambda a: "[" + ",".join("" if (isinstance(x, float) and not np.isfinite(x)) else str(x) for x in a) + "]"  # noqa: E731
    for i in range(len(t)):
        common = rng.normal(0, FLOOR_MAS)
        w = np.r_[np.nan, w0[i] + common + rng.normal(0, sccd[i], 9)]
        e = np.r_[np.nan, np.full(9, sccd[i])]
        ns = ((t[i] - J2010_MJD) * NS_PER_DAY + np.arange(10) * 4.4e9).astype(np.int64)
        rows.append(dict(source_id=str(source_id), transit_id=int(1e15 + i), ra0=ra, dec0=dec, obs_time_tcb=fmt(ns.tolist()),
                         obs_time_bary_corr=0.0, scan_pos_angle=fmt(np.round(np.full(10, np.degrees(theta[i])), 8).tolist()),
                         parallax_factor_al=plx[i], centroid_pos_al=fmt(np.round(w, 5).tolist()),
                         centroid_pos_error_al=fmt(np.round(e, 5).tolist()),
                         used_by_agis_al=fmt(["false"] + ["true"] * 9), blended=fmt(["false"] * 10),
                         multipeak=fmt(["false"] * 10), g_class=1, gates=fmt([0] * 10), transit_proc_flags=0,
                         agis_source_excess_noise=0.0))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- photometry
def photometry(epoch_csv: Path | None, case: str, root: Path, t0: float, te_hi: float) -> tuple[al.PhotData, dict]:
    """Flux ratios to a quiet baseline: Gaia G/BP/RP from the H-0014 cache (flagged transits dropped) and ATLAS o/c for the
    cases that have it. The baseline is the median outside |t - t0| < max(3 tE_hi, 150 d)."""
    parts, info = [], {}
    win = max(3 * (te_hi if np.isfinite(te_hi) else 100.0), 150.0)
    if epoch_csv is not None and epoch_csv.exists():
        e = pd.read_csv(epoch_csv)
        e = e[(e.flag.fillna("") == "") & np.isfinite(e.mag)]
        for band in ("G", "BP", "RP"):
            b = e[e.band == band]
            quiet = b[np.abs(b.t_mjd - t0) > win]
            if len(b) < 5 or len(quiet) < 3:
                continue
            base = float(np.median(quiet.mag))
            f = 10 ** (-0.4 * (b.mag.to_numpy() - base))
            parts.append(pd.DataFrame(dict(t=b.t_mjd, f=f, e=np.maximum(f * b.err.to_numpy() / 1.0857, 1e-3), group=band)))
            info[f"n_{band}"] = len(b)
    p = root / f"cases/{case}/data/atlas.parquet" if case else None
    if p is not None and p.exists():
        a = pd.read_parquet(p)
        a = a[(a.flag.fillna("") == "") & (a.dflux_ujy > 0)]
        a = a.assign(night=np.floor(a.t_mjd)).groupby(["band", "night"]).agg(
            t=("t_mjd", "mean"), fl=("flux_ujy", "mean"), de=("dflux_ujy", lambda x: np.sqrt(np.sum(x**2)) / len(x))).reset_index()
        for band, b in a.groupby("band"):
            quiet = b[np.abs(b.t - t0) > win]
            if len(quiet) < 5:
                continue
            base = float(np.median(quiet.fl))
            if base <= 0:
                continue
            parts.append(pd.DataFrame(dict(t=b.t, f=b.fl / base, e=np.maximum(b.de / base, 2e-3), group=band)))
            info[f"n_{band}"] = len(b)
    if not parts:
        return al.PhotData(np.zeros(0), np.zeros(0), np.zeros(0), np.zeros(0, str)), info
    d = pd.concat(parts, ignore_index=True)
    return al.PhotData(d.t.to_numpy(), d.f.to_numpy(), d.e.to_numpy(), d.group.to_numpy()), info


# ---------------------------------------------------------------- the stage
def _targets(root: Path, idm: pd.DataFrame | None, top: int | None, controls: bool = True) -> pd.DataFrame:
    """The ranked targets (kind "target") followed by the sealed control stars (kind "control", data/controls.csv: Gaia DR3
    stars matched in G and position to the F1 targets, each with a fake event hint)."""
    t = pd.read_csv(root / H15 / "data/ranked_targets.csv", dtype={"source_id": str})
    t = t.sort_values("rank")
    if top:
        t = t.head(top)
    t["kind"] = "target"
    cp = root / H15 / "data/controls.csv"
    if controls and cp.exists():
        c = pd.read_csv(cp, dtype={"source_id": str, "matched_target": str})
        c = c.assign(kind="control", case="", rank=np.nan, piE_lo=np.nan, piE_hi=np.nan)
        t = pd.concat([t, c[[k for k in c.columns if k in t.columns or k in ("matched_target", "kind")]]], ignore_index=True)
    m = dict(zip(idm.dr3_source_id, idm.new_source_id, strict=True)) if idm is not None else {}
    t["release_source_id"] = [m.get(s, s) for s in t.source_id]
    return t


def _fit_one(r, ast: pd.DataFrame, phot: al.PhotData) -> dict:
    wc = ast.wclass.astype(str).to_numpy() if "wclass" in ast and (ast.wclass.astype(str) != "").any() else None
    a = al.AstroData(ast.t_mjd.to_numpy(), ast.theta.to_numpy(), ast.w.to_numpy(), ast.sigma.to_numpy(), ast.plx.to_numpy(), wc)
    te_hint = float(np.sqrt(r.tE_lo * r.tE_hi)) if np.isfinite(r.tE_lo) and np.isfinite(r.tE_hi) else None
    pie = ((r.piE_lo + r.piE_hi) / 2, (r.piE_hi - r.piE_lo) / 4) if np.isfinite(r.piE_lo) and np.isfinite(r.piE_hi) else None
    kw = {} if "G" in set(phot.group.tolist()) else {"fs_ast": 1.0}
    out = al.fit_target(phot, a, float(r.ra), float(r.dec), t0c=float(r.t0), te_hint=te_hint, piE_prior=pie, **kw)
    out["fs"] = json.dumps(out.get("fs", {}))
    return out


def _complete_idmap(run, idm: pd.DataFrame | None) -> pd.DataFrame:
    """The pipeline's DR3 -> release id map, extended with the same rule to H-0015's targets and controls it lacks."""
    from . import catalogue

    t = _targets(run.root, None, None)
    have = set(idm.dr3_source_id) if idm is not None else set()
    todo = sorted(set(t.source_id) - have)
    parts = [idm] if idm is not None else []
    if todo:
        parts.append(catalogue.idmap(run.arc, run.rel, todo))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["dr3_source_id", "new_source_id", "rule"])


def stage(run, top: int | None = None, dry_top: int = 12) -> dict:
    """Run the astrolens stage inside an H-0014 `pipeline.Run`. Returns the status dict for status.json."""
    rel, arc, root = run.rel, run.arc, run.root
    failed: set = set()
    truth: dict = {}
    out = run.path("astrolens/x").parent
    idm = run.idm()
    if not rel.stand_in:
        idm = _complete_idmap(run, idm)          # the controls (and any target the idmap stage missed) need DR4 ids too
        idm.to_csv(out / "idmap.csv", index=False)
    t = _targets(root, idm, top)
    info = {"targets": int((t.kind == "target").sum()), "controls": int((t.kind == "control").sum())}
    status_rows, results = [], []
    t_start = time.time()
    simulated = not rel.has_epoch_astrometry
    if simulated:
        msg = f"epoch astrometry not available in {rel.key} ({rel.name} has no EPOCH_ASTROMETRY product)"
        log.info(msg)
        info["epoch_astrometry"] = msg
        try:  # confirm against the archive what DataLink offers, without failing the stage
            lk = arc.links(str(t.release_source_id.iloc[0]))
            info["datalink_retrieval_types"] = lk["retrieval_types"]
            info["datalink_offers_epoch_astrometry"] = rel.retrieval_epoch_astrometry in lk["retrieval_types"]
        except Exception as e:  # noqa: BLE001
            info["datalink_probe_error"] = f"{type(e).__name__}: {str(e)[:200]}"
        # the dry run: the top targets and a few controls (a control uses its matched target's scanning law: 6' apart)
        t = pd.concat([t[t.kind == "target"].head(dry_top), t[t.kind == "control"].head(max(dry_top // 3, 1))],
                      ignore_index=True)
        gost = pd.read_csv(root / H15 / "data/gost_transits.csv.gz", dtype={"source_id": str})
        rng = np.random.default_rng(15)
        raw_by_id = {}
        for i, r in enumerate(t.itertuples()):
            g = gost[gost.source_id == (r.source_id if r.kind == "target" else r.matched_target)]
            if g.empty:
                continue
            keep = rng.uniform(size=len(g)) < 0.8
            g = g[keep]
            control = i == 0   # positive control: a 10 Msun-like deflection injected in the top target
            pie = (r.piE_lo + r.piE_hi) / 2 / np.sqrt(2) if np.isfinite(r.piE_lo) and np.isfinite(r.piE_hi) else 0.05
            q = np.array([r.t0, float(np.sqrt(r.tE_lo * r.tE_hi)) if np.isfinite(r.tE_lo) else 100.0, 0.3, pie, pie])
            if control:
                q0 = q
            raw_by_id[r.release_source_id] = simulated_raw(r.release_source_id, g.t_mjd.to_numpy(), g.theta.to_numpy(),
                                                          g.plx_al.to_numpy(), float(r.G), rng, q=q if control else None,
                                                          theta_e=5.0 if control else 0.0, fs=0.9, ra=r.ra, dec=r.dec)
        info["simulated_sources"] = len(raw_by_id)
        truth = {str(t.release_source_id.iloc[0]): (q0, 5.0, 0.9)} if len(t) else {}
        info["positive_control"] = str(t.release_source_id.iloc[0]) if len(t) else None
    else:
        # epoch photometry for any of our sources the H-0014 epochs stage did not fetch (the controls, at least)
        need_ph = [s for s in t.release_source_id if s and not (run.out / "epoch" / f"{s}.csv").exists()]
        if need_ph:
            try:
                arc.epoch(need_ph, cache=run.path("epoch/x").parent)
            except Exception as e:  # noqa: BLE001
                arc.error("astrolens.epoch_photometry", f"{type(e).__name__}: {str(e)[:300]}", n_ids=len(need_ph))
        cache = run.path("epoch_astrometry/x").parent
        ids = [s for s in t.release_source_id if s]
        raw_by_id = {}
        todo = [s for s in ids if not (cache / f"{s}.csv").exists()]
        for i in range(0, len(todo), arc.chunk):
            part = todo[i:i + arc.chunk]
            try:
                for raw in arc.epoch_astrometry_raw(part):
                    sid = str(raw.source_id.iloc[0])
                    raw.to_csv(cache / f"{sid}.csv", index=False)
            except Exception as e:  # noqa: BLE001  recorded with its ids; never treated as "no epoch astrometry"
                failed |= set(part)
                arc.error("epoch_astrometry", f"{type(e).__name__}: {str(e)[:300]}", n_ids=len(part), ids=part)
        for s in ids:
            p = cache / f"{s}.csv"
            if p.exists():
                raw_by_id[s] = pd.read_csv(p, dtype={"source_id": str})
        info["fetched"] = len(raw_by_id)
        info["failed_ids"] = len(failed)
    epoch_dir = run.out / "epoch"
    for r in t.itertuples():
        sid = r.release_source_id
        row = dict(kind=r.kind, rank=r.rank, source_id=r.source_id, release_source_id=sid, name=r.name,
                   case=r.case if isinstance(r.case, str) else "", simulated=simulated,
                   matched_target=getattr(r, "matched_target", "") if r.kind == "control" else "")
        raw = raw_by_id.get(sid)
        if raw is None:
            row["status"] = "error: fetch failed" if sid in failed else "no epoch astrometry"
            status_rows.append(row)
            continue
        try:
            ast = normalise(raw, ra=float(r.ra), dec=float(r.dec))
        except ValueError as e:     # FormatError included: a failed sanity check makes the target ineligible
            row["status"] = f"error: {e}"[:300]
            status_rows.append(row)
            continue
        phot, pinfo = photometry(epoch_dir / f"{sid}.csv", row["case"], root, float(r.t0), float(r.tE_hi))
        if simulated and sid in truth:
            # the positive control: Gaia G photometry of the injected event at the same transits
            q, _, fs = truth[sid]
            from ..analysis.lensing import magnification, sun_offsets
            dn_s, de_s = sun_offsets(ast.t_mjd.to_numpy(), r.ra, r.dec, float(round(q[0])))
            tau = (ast.t_mjd.to_numpy() - q[0]) / q[1] + q[3] * dn_s + q[4] * de_s
            beta = q[2] + (-q[3] * de_s + q[4] * dn_s)
            f = fs * magnification(np.hypot(tau, beta)) + 1 - fs
            gp = al.sigma_g_transit(float(r.G))
            phot = al.PhotData(ast.t_mjd.to_numpy(), f + rng.normal(0, gp, len(f)), np.full(len(f), gp), ["G"] * len(f))
            pinfo = {"n_G_simulated": len(f), "positive_control": True}
        elif simulated and "n_G" not in pinfo:
            # the dry run's photometry: the release has none for this source; simulate Gaia G at the same transits
            gp = al.sigma_g_transit(float(r.G))
            phot = al.PhotData(np.r_[phot.t, ast.t_mjd], np.r_[phot.f, 1 + rng.normal(0, gp, len(ast))],
                               np.r_[phot.e, np.full(len(ast), gp)], np.r_[phot.group, ["G"] * len(ast)])
            pinfo["n_G_simulated"] = len(ast)
        row.update(n_transits=len(ast), n_ccd=int(ast.n_ccd.sum()), **pinfo, **quality_summary(ast))
        try:
            res = _fit_one(r, ast, phot)
            row["status"] = "fitted"
            results.append({**row, **res})
        except Exception as e:  # noqa: BLE001
            row["status"] = f"error: fit failed: {type(e).__name__}: {str(e)[:200]}"
        status_rows.append(row)
    st = pd.DataFrame(status_rows)
    st.to_csv(out / "status.csv", index=False)
    res = pd.DataFrame(results)
    res.to_csv(out / "results.csv", index=False)
    info["status_counts"] = st.status.str.split(":").str[0].value_counts().to_dict() if len(st) else {}
    if len(res):
        info["significant_deflections_dchi2_ge_25"] = {k: int((g.dchi2 >= 25).sum()) for k, g in res.groupby("kind")}
        info["top"] = res.sort_values("dchi2", ascending=False)[["name", "dchi2", "theta_e", "M_best", "M_ul95"]].head(5).to_dict("records")
    info["seconds"] = round(time.time() - t_start, 1)
    (out / "summary.json").write_text(json.dumps(info, indent=1, default=str))
    return info
