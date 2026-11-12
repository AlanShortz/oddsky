"""Export cases to static JSON for the web viewer. No backend: the site is files."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from .analysis.stats import daily_bins
from .case.store import CaseStore, _jsonable
from .paths import cases_dir, repo_root

MAX_POINTS = 1500
RECENT_MJD = 55197.0  # 2010-01-01: the default view gets finer sampling than the deep archive
RECENT_POINTS = 2500


def _downsample(good: pd.DataFrame, limit: int) -> tuple[pd.DataFrame, float | None]:
    if len(good) <= limit:
        return good, None
    width = 1.0
    b = daily_bins(good, width)
    while len(b) > limit:
        width *= 2
        b = daily_bins(good, width)
    return b, width


def _clean(o):
    """Strict JSON: NaN/inf become null."""
    if isinstance(o, float):
        return o if np.isfinite(o) else None
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    return o


def series_payload(df: pd.DataFrame) -> dict[str, dict]:
    """One entry per survey:band, downsampled for the browser but never smoothed across gaps."""
    out = {}
    for (survey, band), g in df.groupby(["survey", "band"]):
        good = g[g.flag == ""]
        flagged = g[g.flag != ""]
        old, new = good[good.t_mjd < RECENT_MJD], good[good.t_mjd >= RECENT_MJD]
        po, wo = _downsample(old, MAX_POINTS // 2)
        pn, wn = _downsample(new, RECENT_POINTS)
        pts = pd.concat([po[["t_mjd", "mag", "err"]], pn[["t_mjd", "mag", "err"]]], ignore_index=True)
        binned = max(w for w in (wo, wn) if w) if (wo or wn) else None
        key = f"{survey}:{band}"
        out[key] = {
            "survey": survey,
            "band": band,
            "unit": "relative mag" if survey == "TESS" else "mag",
            "n_raw": int(len(good)),
            "binned_days": binned,
            "t": np.round(pts["t_mjd"].to_numpy(float), 4).tolist(),
            "mag": np.round(pts["mag"].to_numpy(float), 4).tolist(),
            "err": np.round(np.nan_to_num(pts["err"].to_numpy(float), nan=0.0), 4).tolist(),
            "flagged": {
                "n": int(len(flagged)),
                "t": np.round(flagged["t_mjd"].to_numpy(float), 4).tolist()[:500],
                "mag": np.round(flagged["mag"].to_numpy(float), 4).tolist()[:500],
                "why": flagged["flag"].tolist()[:500],
            },
        }
    return out


def case_figures(store: CaseStore) -> list[dict]:
    """Images listed in cases/<id>/figures/index.yaml (file, caption, alt), in that order. Only listed files are
    published: a case whose evidence is not a survey light curve (a transient in another galaxy, say) shows these
    where the interactive figure would be."""
    idx = store.path / "figures" / "index.yaml"
    if not idx.exists():
        return []
    out = []
    for item in yaml.safe_load(idx.read_text()) or []:
        if not (store.path / "figures" / item["file"]).is_file():
            raise FileNotFoundError(f"{idx}: {item['file']} is listed but missing")
        out.append({"file": item["file"], "caption": item.get("caption", ""), "alt": item.get("alt", "")})
    return out


def case_payload(store: CaseStore) -> dict:
    case = store.load()
    series = {}
    for s in store.surveys():
        series.update(series_payload(store.series(s)))
    inv_dir = store.path / "investigations"
    investigations = [
        {"file": p.name, "markdown": p.read_text()} for p in sorted(inv_dir.glob("*.md"))
    ] if inv_dir.exists() else []
    rev_dir = store.path / "reviews"
    reviews = [
        {"file": p.name, "markdown": p.read_text()} for p in sorted(rev_dir.glob("*.md"))
    ] if rev_dir.exists() else []
    skeptic = store.path / "skeptic.json"
    ctx = store.context()
    if "neighbors" in ctx:
        ctx["neighbors"] = ctx["neighbors"][:12]
    if "tess" in ctx:
        for sec in ctx["tess"].get("sectors", {}).values():
            sec["n_desat"] = len(sec.pop("desat_mjd", []))
    return {
        "case": case.model_dump(mode="json", exclude_none=True),
        "series": series,
        "figures": case_figures(store),
        "context": ctx,
        "provenance": store.provenance(),
        "skeptic": json.loads(skeptic.read_text()) if skeptic.exists() else None,
        "ledger": store.ledger(),
        "investigations": investigations,
        "reviews": reviews,
    }


def export_web(out: Path | None = None) -> list[str]:
    out = out or repo_root() / "web" / "data"
    (out / "cases").mkdir(parents=True, exist_ok=True)
    index = []
    for d in sorted(cases_dir().glob("OS-*")):
        if not (d / "case.yaml").exists():
            continue
        store = CaseStore(d)
        payload = case_payload(store)
        payload = _clean(json.loads(json.dumps(payload, default=_jsonable)))
        (out / "cases" / f"{d.name}.json").write_text(json.dumps(payload, allow_nan=False, separators=(",", ":")))
        fig_out = out / "figures" / d.name
        if fig_out.exists():
            shutil.rmtree(fig_out)
        for f in payload["figures"]:
            fig_out.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(d / "figures" / f["file"], fig_out / f["file"])
        c = payload["case"]
        index.append({
            "id": c["id"], "title": c["title"], "hook": c.get("hook", ""), "status": c["status"],
            "target": (c.get("target") or {}).get("name"),
            "series": list(payload["series"]),
            "n_claims": len(c.get("claims", [])), "n_hypotheses": len(c.get("hypotheses", [])),
            "n_predictions": len(c.get("predictions", [])),
            "featured": bool(c.get("featured", False)),
            "hunt": c.get("hunt"),
        })
    trials = repo_root() / "trials"
    scorecards = []
    for f in sorted(trials.glob("*/results/*.json")) if trials.exists() else []:
        scorecards.append(json.loads(f.read_text()))
    (out / "index.json").write_text(json.dumps({"cases": index, "scorecards": scorecards}, default=_jsonable, indent=1))
    from .trials.sky import trial_payload

    page = json.loads((trials / "page.json").read_text()) if (trials / "page.json").exists() else {}
    payloads = [trial_payload(m.parent) for m in sorted(trials.glob("*/manifest.json"))] if trials.exists() else []
    (out / "trials.json").write_text(json.dumps(_clean(json.loads(json.dumps({"trials": payloads, "page": page}, default=_jsonable))),
                                                allow_nan=False, separators=(",", ":")))
    return [i["id"] for i in index]
