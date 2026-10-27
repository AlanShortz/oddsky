"""Export cases to static JSON for the web viewer. No backend: the site is files."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .analysis.stats import daily_bins
from .case.store import CaseStore, _jsonable
from .paths import cases_dir, repo_root

MAX_POINTS = 1500


def series_payload(df: pd.DataFrame) -> dict[str, dict]:
    """One entry per survey:band, downsampled for the browser but never smoothed across gaps."""
    out = {}
    for (survey, band), g in df.groupby(["survey", "band"]):
        good = g[g.flag == ""]
        flagged = g[g.flag != ""]
        if len(good) > MAX_POINTS:
            width = 1.0
            b = daily_bins(good, width)
            while len(b) > MAX_POINTS:
                width *= 2
                b = daily_bins(good, width)
            pts, binned = b, width
        else:
            pts, binned = good, None
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


def case_payload(store: CaseStore) -> dict:
    case = store.load()
    series = {}
    for s in store.surveys():
        series.update(series_payload(store.series(s)))
    inv_dir = store.path / "investigations"
    investigations = [
        {"file": p.name, "markdown": p.read_text()} for p in sorted(inv_dir.glob("*.md"))
    ] if inv_dir.exists() else []
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
        "context": ctx,
        "provenance": store.provenance(),
        "skeptic": json.loads(skeptic.read_text()) if skeptic.exists() else None,
        "ledger": store.ledger(),
        "investigations": investigations,
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
        (out / "cases" / f"{d.name}.json").write_text(json.dumps(payload, default=_jsonable, separators=(",", ":")))
        c = payload["case"]
        index.append({
            "id": c["id"], "title": c["title"], "hook": c.get("hook", ""), "status": c["status"],
            "target": (c.get("target") or {}).get("name"),
            "series": list(payload["series"]),
            "n_claims": len(c.get("claims", [])), "n_hypotheses": len(c.get("hypotheses", [])),
            "n_predictions": len(c.get("predictions", [])),
            "featured": bool(c.get("featured", False)),
        })
    trials = repo_root() / "trials"
    scorecards = []
    for f in sorted(trials.glob("*/results/*.json")) if trials.exists() else []:
        scorecards.append(json.loads(f.read_text()))
    (out / "index.json").write_text(json.dumps({"cases": index, "scorecards": scorecards}, default=_jsonable, indent=1))
    return [i["id"] for i in index]
