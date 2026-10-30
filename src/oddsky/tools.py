"""The Oddsky toolbox: one set of functions behind both the MCP server and `oddsky call`.

Every tool takes a `case` (an id like OS-0001, or a path to a case/trial directory) and returns
plain JSON. Analysis and recording calls are written to the case's ledger.jsonl with a digest of
their result, so any claim can cite the exact computation it rests on, and `oddsky replay` can
re-run it.

Modes: "open" (real stars, archives, literature) and "blind" (a scrubbed trial packet; no
archive, no names, no future data). Set by the server, not by the agent.
"""

from __future__ import annotations

import datetime as dt
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import skeptic as _skeptic
from .analysis import color, excursions, lensing, periodogram, stats
from .case.model import CLASSES, Check, Claim, Hypothesis, Prediction
from .case.store import CaseStore
from .paths import cases_dir

MJD_EPOCH = dt.date(1858, 11, 17)
SURVEY_FILES = {"neowise_exp": "neowise_exp", "gaia": "gaia_epoch", "asas-sn": "asassn", "asassn": "asassn", "aavso": "aavso", "neowise": "neowise",
                "tess": "tess", "ztf": "ztf", "atlas": "atlas"}


class Toolbox:
    def __init__(self, mode: str = "open", blind_root: Path | None = None, author: str | None = None):
        self.mode = mode
        self.blind_root = Path(blind_root).resolve() if blind_root else None
        self.author = author or os.environ.get("ODDSKY_AUTHOR", "unknown-agent")

    # -- plumbing -------------------------------------------------------------------------------
    def store(self, case: str) -> CaseStore:
        if self.mode == "blind":
            root = self.blind_root
            p = (root / case).resolve() if root else Path(case).resolve()
            if root and (root / "case.yaml").exists() and case in (root.name, ".", ""):
                p = root
            if root and root not in (p, *p.parents):
                raise PermissionError("blind mode: cases outside the trial packet are not visible")
            return CaseStore(p)
        return CaseStore.find(case)

    def _frame(self, store: CaseStore, series: str) -> pd.DataFrame:
        survey, _, band = series.partition(":")
        key = SURVEY_FILES.get(survey.strip().lower(), survey.strip().lower())
        df = store.series(key)
        df = df[df.flag == ""]
        if band:
            df = df[df.band.str.lower() == band.strip().lower()]
            if df.empty:
                raw = store.series(key)
                have = sorted(raw.band.unique())
                flags = raw[raw.band.str.lower() == band.strip().lower()].flag.value_counts().to_dict()
                if flags:
                    raise ValueError(f"{series} exists but every point is flagged {flags} (e.g. saturated); "
                                     "there is no usable data in it")
                raise ValueError(f"no series {series}; bands available: {have}")
        elif df.band.nunique() > 1:
            raise ValueError(f"{survey} has several bands {sorted(df.band.unique())}; ask for e.g. '{survey}:{df.band.iloc[0]}'")
        return df

    def _t(self, x: float | str | None, end: bool = False) -> float | None:
        """Accept MJD numbers or ISO dates (open mode only; blind packets use relative days).
        An ISO date used as the end of a window means the end of that (UT) day."""
        if x is None or x == "":
            return None
        if isinstance(x, (int, float)):
            return float(x)
        try:
            return float(x)
        except ValueError:
            if self.mode == "blind":
                raise ValueError("blind mode uses relative days (numbers), not calendar dates") from None
            d = dt.date.fromisoformat(str(x)[:10])
            return float((d - MJD_EPOCH).days) + (0.99999 if end else 0.0)

    def _window(self, df: pd.DataFrame, start, end) -> pd.DataFrame:
        a, b = self._t(start), self._t(end, end=True)
        if a is not None:
            df = df[df.t_mjd >= a]
        if b is not None:
            df = df[df.t_mjd <= b]
        return df

    def _log(self, store: CaseStore, tool: str, args: dict, result: Any) -> Any:
        cid = store.log_call(tool, {k: v for k, v in args.items() if k != "case"}, result, self.author)
        if isinstance(result, dict):
            result = {"call_id": cid, **result}
        return result

    # -- discovery ------------------------------------------------------------------------------
    def list_cases(self) -> dict:
        """List the cases you can investigate, with their status on the discovery ladder."""
        dirs = [self.blind_root] if self.mode == "blind" else sorted(cases_dir().glob("OS-*"))
        out = []
        for d in dirs:
            if d and (d / "case.yaml").exists():
                c = CaseStore(d).load()
                out.append({"case": c.id, "title": c.title, "status": c.status, "hook": c.hook,
                            "claims": len(c.claims), "hypotheses": len(c.hypotheses)})
        return {"mode": self.mode, "cases": out}

    def list_classes(self, case: str | None = None) -> dict:
        """The Strange Stars explanation classes. Hypotheses must use one of these names."""
        return {"classes": CLASSES}

    def case_overview(self, case: str) -> dict:
        """Start here. What the case is, what data exist (per series: span, points, brightness range),
        the stellar context from Gaia, and the claims and hypotheses recorded so far."""
        s = self.store(case)
        c = s.load()
        series = {}
        for survey in s.surveys():
            df = s.series(survey)
            for band, g in df.groupby("band"):
                good = g[g.flag == ""]
                if good.empty:
                    continue
                d = stats.describe(good)
                d = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items() if k != "note"}
                d["n_flagged"] = int((g.flag != "").sum())
                series[f"{good.survey.iloc[0] if len(good) else survey.upper()}:{band}"] = d
        ctx = s.context()
        prov = {k: {"archive": v.get("archive"), "status": v.get("status"), "notes": v.get("notes", [])[:3]}
                for k, v in s.provenance().items()}
        out = {
            "case": c.id, "mode": self.mode, "title": c.title, "status": c.status, "summary": c.summary,
            "target": c.target.model_dump(exclude_none=True) if c.target and self.mode == "open" else "hidden (blind trial)",
            "time_convention": "MJD" if self.mode == "open" else "relative days (day 0 = first observation)",
            "magnitudes": "larger = fainter; TESS series are relative to each sector's median",
            "series": series,
            "gaia_context": ctx.get("gaia"),
            "gaia_variability": ctx.get("gaia_variability"),
            "n_neighbors_within_30_arcsec": len(ctx.get("neighbors", [])),
            "provenance": prov,
            "claims": [cl.model_dump(include={"id", "tag", "text", "calls", "retracted"}, exclude_none=True)
                       for cl in c.claims],
            "hypotheses": [h.model_dump(include={"id", "klass", "status", "confidence", "statement", "supports",
                                                 "conflicts", "would_falsify"}) for h in c.hypotheses],
            "predictions": [p.model_dump(include={"id", "statement", "probability"}) for p in c.predictions],
            "advice": "Run skeptic_report early. Tag claims honestly: observed (straight from data), computed "
                      "(a tool's output), inferred (reasoning from evidence), speculated (a guess).",
        }
        return self._log(s, "case_overview", {"case": case}, out)

    # -- looking at data ------------------------------------------------------------------------
    def get_lightcurve(self, case: str, series: str, start: float | str | None = None,
                       end: float | str | None = None, bin_days: float = 0.0, max_points: int = 300) -> dict:
        """Points of one series, e.g. series='NEOWISE:W1' or 'AAVSO:V'. Optional time window and
        binning (median per bin_days). Long series are binned automatically to max_points."""
        s = self.store(case)
        df = self._frame(s, series)
        a, b = self._t(start), self._t(end, end=True)
        if a is not None:
            df = df[df.t_mjd >= a]
        if b is not None:
            df = df[df.t_mjd <= b]
        width = bin_days
        b_df = stats.daily_bins(df, width) if width else df
        while len(b_df) > max_points:
            width = max(width * 2, 1.0)
            b_df = stats.daily_bins(df, width)
        cols = [c for c in ("t_mjd", "mag", "err", "n", "n_exp", "observers") if c in b_df]
        pts = b_df[cols].round(4).to_dict(orient="records")
        out = {"series": series, "n_points_raw": int(len(df)), "binned_days": width or None,
               "columns": cols, "points": [[p[c] for c in cols] for p in pts]}
        return self._log(s, "get_lightcurve", dict(case=case, series=series, start=start, end=end,
                                                    bin_days=bin_days, max_points=max_points), out)

    def describe_series(self, case: str, series: str) -> dict:
        """Summary statistics, long-term slope, and the single most significant change in level
        (a changepoint: when, how big, which direction) for one series."""
        s = self.store(case)
        df = self._frame(s, series)
        out = {"series": series, "stats": stats.describe(df), "changepoint": stats.changepoint(df)}
        return self._log(s, "describe_series", dict(case=case, series=series), out)

    def compare_windows(self, case: str, series: str, a_start: float | str, a_end: float | str,
                        b_start: float | str, b_end: float | str) -> dict:
        """Median brightness of a series in window A vs window B, with the significance of the difference."""
        s = self.store(case)
        df = self._frame(s, series)
        wa = stats.window_stat(df, self._t(a_start), self._t(a_end, end=True))
        wb = stats.window_stat(df, self._t(b_start), self._t(b_end, end=True))
        out: dict = {"series": series, "a": wa, "b": wb}
        if wa.get("n") and wb.get("n"):
            d = wb["median"] - wa["median"]
            e = float(np.hypot(wa["err_of_median"], wb["err_of_median"]))
            out["b_minus_a_mag"] = d
            out["significance_sigma"] = abs(d) / e if e > 0 else None
            out["reading"] = "positive = fainter in B"
        return self._log(s, "compare_windows", dict(case=case, series=series, a_start=a_start, a_end=a_end,
                                                     b_start=b_start, b_end=b_end), out)

    def observer_agreement(self, case: str, series: str, baseline_start: float | str, baseline_end: float | str,
                           start: float | str, end: float | str, min_points: int = 3) -> dict:
        """Does every independent observer see the same thing? For each AAVSO observer (or camera) with
        data in both windows: their own baseline median, their faintest and median point in the event
        window, and the depth relative to their own baseline. Observer zero points cancel."""
        s = self.store(case)
        df = self._frame(s, series)
        who = "observer" if "observer" in df else "camera" if "camera" in df else None
        if who is None:
            raise ValueError(f"{series} has no observer or camera column")
        base = self._window(df, baseline_start, baseline_end)
        ev = self._window(df, start, end)
        rows = []
        for obs, g in ev.groupby(who):
            b = base[base[who] == obs]
            if len(g) >= min_points and len(b) >= 5:
                bm = float(np.median(b.mag))
                rows.append({who: str(obs), "n_event": int(len(g)), "n_baseline": int(len(b)), "baseline": round(bm, 3),
                             "depth_faintest": round(float(g.mag.max()) - bm, 3),
                             "depth_median": round(float(np.median(g.mag)) - bm, 3)})
        rows.sort(key=lambda r: -r["n_event"])
        d = np.array([r["depth_faintest"] for r in rows])
        out = {"series": series, "group_by": who, "n_independent": len(rows), "per_source": rows[:25]}
        if len(d):
            out.update(depth_median_over_sources=float(np.median(d)), depth_spread_robust=float(stats.robust_std(d))
                       if len(d) > 2 else None)
        return self._log(s, "observer_agreement", dict(case=case, series=series, baseline_start=baseline_start,
                                                        baseline_end=baseline_end, start=start, end=end,
                                                        min_points=min_points), out)

    def eclipse_period(self, case: str, series: list[str], depth: float = 0.3, p_min: float = 0.2,
                       p_max: float = 300.0) -> dict:
        """Period of short, deep, rare events (eclipses) that Lomb-Scargle misses: find the period at which
        every point more than `depth` mag below its series median falls at one phase, and no quiet point
        does. Combine instruments (e.g. ["ZTF:ZTF_r", "GAIA:G"]) for a long-baseline ephemeris."""
        s = self.store(case)
        dims, quiets, t_all = [], [], []
        for ser in series:
            df = self._frame(s, ser)
            if df.empty:
                continue
            med = float(np.median(df.mag))
            dims.append(df.t_mjd[df.mag > med + depth].to_numpy())
            quiets.append(df.t_mjd[df.mag < med + 0.05].to_numpy())
            t_all.append(df.t_mjd.to_numpy())
        td, tq = np.concatenate(dims), np.concatenate(quiets)
        if len(td) < 4:
            return {"error": f"only {len(td)} points deeper than {depth} mag"}
        span = float(np.ptp(np.concatenate(t_all)))
        n = int(min(2_000_000, max(20_000, 20 * span * (1 / p_min - 1 / p_max))))
        freqs = np.linspace(1 / p_max, 1 / p_min, n)
        best = (-1.0, None)
        for chunk in np.array_split(freqs, max(1, n // 2000)):
            ph = (td[None, :] * chunk[:, None]) % 1.0
            ang = 2 * np.pi * ph
            mu = (np.arctan2(np.sin(ang).mean(1), np.cos(ang).mean(1)) / (2 * np.pi)) % 1.0
            dd = np.abs((ph - mu[:, None] + 0.5) % 1.0 - 0.5)
            phq = (tq[None, :] * chunk[:, None]) % 1.0
            dq = np.abs((phq - mu[:, None] + 0.5) % 1.0 - 0.5)
            score = (dd < 0.04).mean(1) - 3 * (dq < 0.02).mean(1)
            k = int(np.argmax(score))
            if score[k] > best[0]:
                best = (float(score[k]), float(chunk[k]), float(mu[k]), float((dd[k] < 0.04).mean()), float((dq[k] < 0.02).mean()))
        sc, f, mu, frac, contam = best
        P = 1 / f
        T0 = (np.floor(td.min() / P) + mu) * P
        # Missing-eclipse test: if the true period is k*P, some cycles (by cycle number mod k) are
        # observed flat at the predicted eclipse time. Folding at P/k hides this; counting cycles does not.
        t_q = np.concatenate([tq, td])
        cyc = np.round((t_q - T0) / P).astype(int)
        near = np.abs(t_q - (T0 + cyc * P)) < 0.01 * P
        deep_c = set(np.round((td - T0) / P).astype(int))
        seen = sorted(set(cyc[near]))
        multiples = {}
        for k in range(2, 7):
            res = {}
            for c in seen:
                r = c % k
                res.setdefault(r, [0, 0])
                res[r][0] += 1
                res[r][1] += int(c in deep_c)
            fr = {int(r): round(d / n, 2) for r, (n, d) in res.items() if n >= 3}
            if len(fr) >= 2 and max(fr.values()) > 0.8 and min(fr.values()) < 0.2:
                multiples[k] = fr
        warn = (f"eclipses missing on some cycles: the true period is probably {min(multiples)} x {P:.5f} d "
                f"(deep fraction by cycle mod k: {multiples[min(multiples)]})") if multiples else None
        phases = np.round(np.sort(np.abs(((td - T0) / P + 0.5) % 1 - 0.5)), 4)
        out = {"series": series, "n_dim": int(len(td)), "n_quiet": int(len(tq)), "baseline_days": span,
               "period_days": P, "t0_mjd": float(T0), "frac_dim_within_0.04_phase": frac,
               "frac_quiet_in_core": contam, "score": sc, "resolution_days": P * P / span,
               "dim_phases": phases.tolist()[:60],
               "cycles_sampled_at_eclipse": len(seen), "period_multiple_warning": warn,
               "reading": "score near 1 = every deep point at one phase and none of the quiet ones. Folding can stack a "
                          "primary and a secondary eclipse at P/k: read period_multiple_warning, and fold at the "
                          "multiples before believing P."}
        return self._log(s, "eclipse_period", dict(case=case, series=series, depth=depth, p_min=p_min, p_max=p_max), out)

    def fold(self, case: str, series: str, period: float, t0: float, window_phase: float = 0.012,
             n_bins: int = 50) -> dict:
        """Fold a series on a period: phase-binned medians, primary depth (phase 0) and secondary depth
        (phase 0.5) within +/- window_phase, the faintest bin away from the primary (a secondary at any
        phase, for eccentric orbits), and primary depth on even vs odd cycles (catches period halving)."""
        s = self.store(case)
        df = self._frame(s, series)
        t, m = df.t_mjd.to_numpy(float), df.mag.to_numpy(float)
        cyc = np.round((t - t0) / period).astype(int)
        ph = (t - t0) / period - cyc
        phu = ph % 1.0
        out_mask = (np.abs(ph) > 0.1)
        base = float(np.median(m[out_mask])) if out_mask.any() else float(np.median(m))
        scatter = float(stats.robust_std(m[out_mask]))

        def depth(sel):
            n = int(sel.sum())
            return {"n": n, "median_delta": round(float(np.median(m[sel]) - base), 4) if n else None,
                    "max_delta": round(float(np.max(m[sel]) - base), 4) if n else None,
                    "err_of_median": round(scatter * 1.2533 / np.sqrt(n), 4) if n else None}

        prim = np.abs(ph) < window_phase
        sec = np.abs(phu - 0.5) < window_phase
        edges = np.linspace(0, 1, n_bins + 1)
        bins = []
        for lo, hi in zip(edges[:-1], edges[1:], strict=True):
            sel = (phu >= lo) & (phu < hi)
            bins.append([round(float((lo + hi) / 2), 4), int(sel.sum()),
                         round(float(np.median(m[sel]) - base), 4) if sel.any() else None])
        away = [b for b in bins if b[2] is not None and b[1] >= 5 and 0.08 < b[0] < 0.92]
        worst = max(away, key=lambda b: b[2]) if away else None
        out = {"series": series, "period_days": period, "t0_mjd": t0, "baseline_mag": base, "out_of_eclipse_scatter": scatter,
               "primary": depth(prim), "secondary_at_phase_0.5": depth(sec),
               "faintest_bin_away_from_primary": {"phase": worst[0], "n": worst[1], "delta": worst[2]} if worst else None,
               "primary_even_cycles": depth(prim & (cyc % 2 == 0)), "primary_odd_cycles": depth(prim & (cyc % 2 == 1)),
               "bins": bins}
        return self._log(s, "fold", dict(case=case, series=series, period=period, t0=t0, window_phase=window_phase,
                                         n_bins=n_bins), out)

    def lens_fit(self, case: str, series: list[str], start: float | str, end: float | str, parallax: bool = True,
                 blend: bool = False, baseline_start: float | str | None = None, baseline_end: float | str | None = None) -> dict:
        """Fit a gravitational microlensing event: a point source magnified by a point lens, without and (by default) with
        annual parallax, to one or more series at once (e.g. ["ATLAS:ATLAS_o", "ATLAS:ATLAS_c", "NEOWISE:W1"]). Each series
        is binned per night and turned into flux / its own baseline (median outside [start, end], or over the baseline window).
        Errors include that series' baseline night-to-night scatter and 1% of flux. Returns t0, tE, u0, A_max (and piE, fs),
        95% ranges for t0 and tE from chi-square profiles (not covariance), how well the peak and wings are sampled, and how
        much the parallax model improves on the static one. A static fit much worse than the parallax fit means the light curve
        is asymmetric; a peak with no points means t0 and A_max rest on the wings. Microlensing is achromatic: fit the bands
        together and compare their residuals."""
        s = self.store(case)
        c = s.load()
        a, b = self._t(start), self._t(end, end=True)
        ts, fs_, es, gs = [], [], [], []
        per = {}
        for ser in series:
            df = stats.daily_bins(self._frame(s, ser), 1.0)
            if self._t(baseline_start) is not None and self._t(baseline_end, end=True) is not None:
                base_df = df[(df.t_mjd >= self._t(baseline_start)) & (df.t_mjd <= self._t(baseline_end, end=True))]
            else:
                base_df = df[(df.t_mjd < a) | (df.t_mjd > b)]
            if len(base_df) < 5:
                raise ValueError(f"{ser}: fewer than 5 baseline nights; give a baseline window")
            m0 = float(np.median(base_df.mag))
            ratio_base = 10 ** (-0.4 * (base_df.mag.to_numpy(float) - m0))
            floor = max(float(stats.robust_std(ratio_base)), 0.005)
            w = df[(df.t_mjd >= a) & (df.t_mjd <= b)]
            if w.empty:
                raise ValueError(f"{ser}: no data between start and end")
            f = 10 ** (-0.4 * (w.mag.to_numpy(float) - m0))
            e = np.sqrt((0.921 * f * w.err.to_numpy(float)) ** 2 + floor**2 + (0.01 * f) ** 2)
            ts.append(w.t_mjd.to_numpy(float))
            fs_.append(f)
            es.append(e)
            gs += [ser] * len(w)
            per[ser] = {"baseline_mag": round(m0, 4), "baseline_scatter_frac": round(floor, 4), "n_nights": int(len(w)),
                        "peak_ratio_observed": round(float(f.max()), 3)}
        t, f, e = np.concatenate(ts), np.concatenate(fs_), np.concatenate(es)
        ra = c.target.ra if c.target else None
        dec = c.target.dec if c.target else None
        out = {"series": per, "n_points": int(len(t))}
        fits = {}
        for name, par in (("static", False), ("parallax", True)) if parallax else (("static", False),):
            prob = lensing.Problem(t, f, e, gs, ra=ra, dec=dec, parallax=par, blend=blend)
            p, chi2 = prob.fit()
            dof = int(len(t) - len(p))
            r = {"t0_mjd": round(float(p[0]), 2), "tE_days": round(float(p[1]), 2), "u0": round(float(p[2]), 4),
                 "A_max": round(float(lensing.magnification(abs(p[2]))), 3), "chi2": round(chi2, 1), "dof": dof}
            if par:
                r.update({"piE_N": round(float(p[3]), 3), "piE_E": round(float(p[4]), 3),
                          "piE": round(float(np.hypot(p[3], p[4])), 3), "t0par_mjd": prob.t0par})
            if blend:
                r["fs"] = {n: round(float(v), 3) for n, v in zip(prob.names, p[prob.nlens:], strict=True)}
            resid = (f - prob.model(p)) / f
            r["mean_residual_by_series"] = {g: round(float(resid[np.asarray(gs) == g].mean()), 4) for g in prob.names}
            fits[name] = (prob, p, chi2, r)
            out[name] = r
        name = "parallax" if parallax else "static"
        prob, p, chi2, r = fits[name]
        t0lo, t0hi, t0open = lensing.profile_range(prob, p, chi2, 0, max(0.6 * p[1], 5.0))
        telo, tehi, teopen = lensing.profile_range(prob, p, chi2, 1, max(0.7 * p[1], 5.0))
        out["ranges_95"] = {"model": name, "t0_mjd": [round(t0lo, 1), round(t0hi, 1)], "tE_days": [round(telo, 1), round(tehi, 1)],
                            "open_ended": bool(t0open or teopen),
                            "note": "profile ranges, chi-square rescaled to 1 per dof; open_ended means the scan hit its edge"}
        cov = lensing.coverage(t, p[0], p[1], p[2])
        out["coverage"] = cov
        warn = []
        if cov["n_peak"] == 0:
            warn.append("no data in the peak: t0 and A_max rest on the wings")
        if cov["n_rise"] < 3:
            warn.append("the rise is barely sampled")
        if parallax and out["static"]["chi2"] - out["parallax"]["chi2"] > 25:
            warn.append(f"the static model is worse by chi2 {out['static']['chi2'] - out['parallax']['chi2']:.0f}: the light curve is "
                        "asymmetric; parallax is one explanation, a binary source (xallarap) or calibration offsets between series are others")
        if r["chi2"] / max(r["dof"], 1) > 3:
            warn.append("chi2/dof > 3: errors underestimated or the model is incomplete")
        out["warnings"] = warn
        return self._log(s, "lens_fit", dict(case=case, series=series, start=start, end=end, parallax=parallax, blend=blend,
                                             baseline_start=baseline_start, baseline_end=baseline_end), out)

    def periodogram(self, case: str, series: str, min_period: float = 0.5, max_period: float | None = None,
                    start: float | str | None = None, end: float | str | None = None) -> dict:
        """Lomb-Scargle periodogram with the survey's spectral window, flagging peaks that match
        Earth/spacecraft rhythms (day, lunar month, TESS orbit, year) or window aliases."""
        s = self.store(case)
        out = periodogram.periodogram(self._window(self._frame(s, series), start, end), min_period, max_period)
        return self._log(s, "periodogram", dict(case=case, series=series, min_period=min_period,
                                                 max_period=max_period, start=start, end=end), out)

    def find_excursions(self, case: str, series: str, baseline_days: float = 300.0, k_sigma: float = 4.0,
                        min_depth: float = 0.05, start: float | str | None = None,
                        end: float | str | None = None) -> dict:
        """Find dips (fainter) and brightenings against a running baseline: start, end, depth,
        ingress/egress durations, asymmetry, and whether the start or end fell in a data gap.
        Restrict to a window (start/end) to get a local noise level, e.g. for quiet years."""
        s = self.store(case)
        df = self._window(self._frame(s, series), start, end)
        bin_days = 0.02 if df.survey.iloc[0] == "TESS" else 1.0
        out = excursions.excursions(df, baseline_days, k_sigma, min_depth, bin_days=bin_days)
        return self._log(s, "find_excursions", dict(case=case, series=series, baseline_days=baseline_days,
                                                     k_sigma=k_sigma, min_depth=min_depth, start=start, end=end), out)

    def cross_band(self, case: str, series_a: str, series_b: str, tolerance_days: float = 5.0,
                   start: float | str | None = None, end: float | str | None = None) -> dict:
        """How series A changes when series B changes (near-simultaneous pairs): correlation and
        slope dA/dB, with the interstellar-dust expectation for comparison."""
        s = self.store(case)
        a = self._window(self._frame(s, series_a), start, end)
        b = self._window(self._frame(s, series_b), start, end)
        out = color.cross_band(a, b, series_a.split(":")[-1], series_b.split(":")[-1], tolerance_days)
        return self._log(s, "cross_band", dict(case=case, series_a=series_a, series_b=series_b,
                                                tolerance_days=tolerance_days, start=start, end=end), out)

    def wise_color(self, case: str) -> dict:
        """NEOWISE W1-W2 colour per visit and whether it tracks W1 brightness (warm dust signature)."""
        s = self.store(case)
        df = s.series("neowise")
        out = color.wise_color(df[df.flag == ""])
        return self._log(s, "wise_color", dict(case=case), out)

    def ir_excess(self, case: str, baseline_start: float | str, baseline_end: float | str,
                  start: float | str, end: float | str) -> dict:
        """Infrared excess in NEOWISE over a baseline (photosphere) epoch: excess flux in each band as a
        fraction of the star, and the blackbody temperature of the excess from its W1/W2 ratio."""
        s = self.store(case)
        df = s.series("neowise")
        out = color.ir_excess(df[df.flag == ""], (self._t(baseline_start), self._t(baseline_end, end=True)),
                              (self._t(start), self._t(end, end=True)))
        return self._log(s, "ir_excess", dict(case=case, baseline_start=baseline_start, baseline_end=baseline_end,
                                               start=start, end=end), out)

    def neighbors(self, case: str, radius_arcsec: float = 30.0) -> dict:
        """Gaia DR3 sources near the target: separation, brightness difference, and fraction of the
        target's flux. In blind mode, identities are removed."""
        s = self.store(case)
        nbs = [n for n in s.context().get("neighbors", []) if n["sep_arcsec"] <= radius_arcsec]
        out = {"radius_arcsec": radius_arcsec, "neighbors": nbs,
               "beams_arcsec": {"WISE W1": 6.1, "ASAS-SN": 16, "TESS pixel": 21, "AAVSO CCD": "~3-5"}}
        return self._log(s, "neighbors", dict(case=case, radius_arcsec=radius_arcsec), out)

    def skeptic_report(self, case: str) -> dict:
        """Run the Skeptic: deterministic checks for blends, saturation, quality cuts, single-observer
        data, survey-rhythm aliases, unobserved onsets, TESS spacecraft systematics and more."""
        s = self.store(case)
        out = _skeptic.run(s)
        return self._log(s, "skeptic_report", dict(case=case), out)

    # -- recording the argument ------------------------------------------------------------------
    def add_claim(self, case: str, text: str, tag: str, calls: list[str] | None = None) -> dict:
        """Record a claim. tag must be observed | computed | inferred | speculated. Cite the call_id(s)
        of the tool results it rests on (computed and observed claims without calls are weak)."""
        s = self.store(case)
        c = s.load()
        known = {e["id"] for e in s.ledger()}
        missing = [k for k in calls or [] if k not in known]
        if missing:
            raise ValueError(f"unknown call ids {missing}; cite call_id values returned by tools")
        claim = Claim(id=c.next_id("C", c.claims), text=text, tag=tag, calls=calls or [], author=self.author)
        c.claims.append(claim)
        s.save(c)
        warn = "computed/observed claim cites no tool call" if tag in ("computed", "observed") and not calls else None
        return self._log(s, "add_claim", dict(case=case, id=claim.id, tag=tag),
                         {"claim": claim.id, **({"warning": warn} if warn else {})})

    def retract_claim(self, case: str, claim: str, reason: str) -> dict:
        """Retract a claim you no longer stand behind (a mistake, a probe, a superseded number). It stays in
        the record, struck through, with your reason. Nothing in Oddsky is silently deleted."""
        s = self.store(case)
        c = s.load()
        cl = next((x for x in c.claims if x.id == claim), None)
        if cl is None:
            raise ValueError(f"no claim {claim}")
        cl.retracted = reason or "retracted"
        s.save(c)
        return self._log(s, "retract_claim", dict(case=case, claim=claim, reason=reason), {"ok": True})

    def add_hypothesis(self, case: str, klass: str, statement: str, supports: list[str] | None = None,
                       conflicts: list[str] | None = None, would_falsify: str = "",
                       confidence: float | None = None) -> dict:
        """Propose an explanation. klass from list_classes(). List claim ids that support it and that are
        in tension with it, and say what observation would falsify it."""
        if klass not in CLASSES:
            raise ValueError(f"klass must be one of {list(CLASSES)}")
        s = self.store(case)
        c = s.load()
        ids = {cl.id for cl in c.claims}
        bad = [x for x in (supports or []) + (conflicts or []) if x not in ids]
        if bad:
            raise ValueError(f"unknown claim ids {bad}")
        both = set(supports or []) & set(conflicts or [])
        if both:
            raise ValueError(f"claims {sorted(both)} listed as both support and conflict; pick one")
        h = Hypothesis(id=c.next_id("H", c.hypotheses), klass=klass, statement=statement, supports=supports or [],
                       conflicts=conflicts or [], would_falsify=would_falsify, confidence=confidence,
                       author=self.author)
        c.hypotheses.append(h)
        s.save(c)
        return self._log(s, "add_hypothesis", dict(case=case, id=h.id, klass=klass), {"hypothesis": h.id})

    def update_hypothesis(self, case: str, hypothesis: str, status: str, confidence: float | None = None,
                          reason: str = "") -> dict:
        """Change a hypothesis's status (live | favored | disfavored | rejected) and confidence, with a reason."""
        s = self.store(case)
        c = s.load()
        h = next((h for h in c.hypotheses if h.id == hypothesis), None)
        if h is None:
            raise ValueError(f"no hypothesis {hypothesis}")
        h.status = status
        if confidence is not None:
            h.confidence = confidence
        s.save(c)
        return self._log(s, "update_hypothesis", dict(case=case, hypothesis=hypothesis, status=status,
                                                       confidence=confidence, reason=reason), {"ok": True})

    def register_prediction(self, case: str, statement: str, probability: float, series: str,
                            start: float | str, end: float | str, op: str, value: float,
                            statistic: str = "median", baseline_start: float | str | None = None,
                            baseline_end: float | str | None = None, hypothesis: str | None = None,
                            resolve_by: str | None = None) -> dict:
        """Register a falsifiable, machine-checkable prediction. Example: 'the median of AAVSO:V between
        start and end will be more than 0.3 mag fainter (op '>', value 0.3) than its median over the
        baseline window'. Without a baseline, value is an absolute magnitude. probability = your stated
        chance the check comes out true. The registration time is sealed by the ledger and git."""
        s = self.store(case)
        c = s.load()
        base = None
        if baseline_start is not None and baseline_end is not None:
            base = (self._t(baseline_start), self._t(baseline_end, end=True))
        chk = Check(series=series, start=self._t(start), end=self._t(end, end=True), statistic=statistic, baseline=base,
                    op=op, value=value)
        try:
            self._frame(s, series)  # validate the series exists
        except FileNotFoundError:
            # A prediction about data the archive has not released yet (e.g. Gaia DR4 epoch photometry) is allowed
            # for archives the grader can fetch; it stays pending until the data exist.
            if series.partition(":")[0].strip().lower() not in SURVEY_FILES:
                raise
        p = Prediction(id=c.next_id("P", c.predictions), hypothesis=hypothesis, statement=statement, check=chk,
                       probability=probability, resolve_by=resolve_by, author=self.author)
        c.predictions.append(p)
        s.save(c)
        return self._log(s, "register_prediction", dict(case=case, id=p.id, check=chk.model_dump()),
                         {"prediction": p.id, "check": chk.model_dump()})

    def check_prediction(self, case: str, prediction: str, dry_run: bool = False) -> dict:
        """Grade a registered prediction against the data now in the case. Predictions whose window has
        not closed yet are reported as pending and not graded. dry_run=True never writes. (Not
        available in blind trials, where the future is held back.)"""
        if self.mode == "blind":
            raise PermissionError("blind mode: predictions are graded after the trial, against held-back data")
        s = self.store(case)
        c = s.load()
        p = next((p for p in c.predictions if p.id == prediction), None)
        if p is None or p.check is None:
            raise ValueError(f"no machine-checkable prediction {prediction}")
        frame = self._frame(s, p.check.series)
        if frame.empty or frame.t_mjd.max() < p.check.end:
            last = float(frame.t_mjd.max()) if len(frame) else None
            return {"prediction": prediction, "outcome": "pending",
                    "note": f"window closes at MJD {p.check.end:.1f}; latest data MJD {last}"}
        res = evaluate(p.check, lambda ser: self._frame(s, ser))
        if dry_run:
            return {"prediction": prediction, "dry_run": True, **res.model_dump()}
        p.resolution = res
        s.save(c)
        return self._log(s, "check_prediction", dict(case=case, prediction=prediction),
                         p.resolution.model_dump())

    # -- open-mode only ---------------------------------------------------------------------------
    def open_case(self, name: str, title: str | None = None, fetch_data: bool = True) -> dict:
        """Open a new case on any star by name (SIMBAD/AAVSO resolvable) and fetch its data from
        Gaia, NEOWISE, AAVSO, ZTF, ASAS-SN and TESS. Takes a minute or two."""
        self._open_only()
        from .fetch import fetch, open_case

        s = open_case(name, title)
        rep = fetch(s) if fetch_data else {}
        return {"case": s.path.name, "fetched": rep}

    def literature(self, case: str) -> dict:
        """Recent papers mentioning the target (SIMBAD bibliography). Open mode only. Read them after
        forming your own view, not before, if you want your investigation to count as independent."""
        self._open_only()
        from .data import simbad

        s = self.store(case)
        c = s.load()
        refs = simbad.bibliography(c.target.name) if c.target else []
        if not refs and c.target:
            for a in c.target.aliases[:3]:
                refs = simbad.bibliography(a)
                if refs:
                    break
        return self._log(s, "literature", dict(case=case), {"references": refs})

    def _open_only(self):
        if self.mode != "open":
            raise PermissionError("not available in blind mode")


def evaluate(check: Check, frame: Callable[[str], pd.DataFrame]):
    """Grade a Check against data. Shared by check_prediction and trial scoring."""
    from .case.model import Resolution

    df = frame(check.series)
    win = df[(df.t_mjd >= check.start) & (df.t_mjd <= check.end)]
    w = win.mag.to_numpy(float)
    if len(w) < 3:
        return Resolution(outcome="unresolvable", n_points=int(len(w)), note="fewer than 3 points in the window")
    # Extremes use nightly medians: robust to a single bad point, but a one-night outburst still counts.
    # (Grader v1 used the 2nd/98th percentile of all points, which let dense quiescent sampling hide short
    # outbursts. Changed after Trial 001; both gradings are published.)
    nightly = stats.daily_bins(win, 1.0).mag.to_numpy(float)
    val = {"median": np.median(w), "faintest": nightly.max(), "brightest": nightly.min(),
           "amplitude": nightly.max() - nightly.min()}[check.statistic]
    note = f"{check.statistic} over window = {val:.3f} ({len(w)} points, {len(nightly)} nights)"
    if check.baseline:
        bw = df[(df.t_mjd >= check.baseline[0]) & (df.t_mjd <= check.baseline[1])].mag.to_numpy(float)
        if len(bw) < 3:
            return Resolution(outcome="unresolvable", n_points=int(len(w)), note="fewer than 3 points in the baseline")
        if check.statistic != "amplitude":
            val = val - np.median(bw)
            note += f"; minus baseline median {np.median(bw):.3f}"
    ok = val > check.value if check.op == ">" else val < check.value
    return Resolution(outcome="true" if ok else "false", observed=float(val), n_points=int(len(w)), note=note)


OPEN_TOOLS = ["list_cases", "list_classes", "case_overview", "get_lightcurve", "describe_series", "compare_windows",
              "observer_agreement", "eclipse_period", "fold", "lens_fit", "periodogram", "find_excursions", "cross_band", "wise_color", "ir_excess", "neighbors",
              "skeptic_report", "add_claim", "retract_claim", "add_hypothesis", "update_hypothesis", "register_prediction", "check_prediction",
              "open_case", "literature"]
BLIND_TOOLS = [t for t in OPEN_TOOLS if t not in ("check_prediction", "open_case", "literature")]


def available(mode: str) -> list[str]:
    return BLIND_TOOLS if mode == "blind" else OPEN_TOOLS
