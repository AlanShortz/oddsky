"""Turn real cases into blind trial packets."""

from __future__ import annotations

import json
import secrets
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from ..case.model import CLASSES, Case
from ..case.store import CaseStore
from .seal import seal

KEEP_GAIA = ("G", "bp_rp", "parallax_over_error", "ruwe", "teff_gspphot", "abs_G", "distance_pc", "non_single_star")
KEEP_NEIGHBOR = ("sep_arcsec", "phot_g_mean_mag", "bp_rp", "dG", "flux_ratio_G", "ruwe")


def scrub_series(df: pd.DataFrame, t0: float, cutoff: float | None, pseudonyms: dict) -> pd.DataFrame:
    df = df.copy()
    if cutoff is not None:
        df = df[df.t_mjd < cutoff]
    df["t_mjd"] = df["t_mjd"] - t0
    if "observer" in df:
        df["observer"] = df["observer"].map(lambda o: pseudonyms.setdefault(o, f"O{len(pseudonyms) + 1}"))
    if "camera" in df and (df.survey == "TESS").any():
        sectors = {s: f"S{chr(97 + i)}" for i, s in enumerate(sorted(df.camera.unique()))}
        df["camera"] = df["camera"].map(sectors)
    return df


def salt_tess_dumps(df: pd.DataFrame, desat: list[float], depth: float, width: float, rng) -> tuple[pd.DataFrame, list]:
    """Fool's gold: plant dips on top of reaction-wheel momentum dumps, the classic TESS impostor.

    Real data, real dump times, fake astrophysics. A careful investigator (or the Skeptic) should
    notice that every dip sits on a spacecraft event."""
    df = df.copy()
    planted = []
    times = sorted(desat)
    # Dumps come in bursts of flagged cadences; keep one time per event.
    events = [t for i, t in enumerate(times) if i == 0 or t - times[i - 1] > 0.5]
    for t in rng.choice(events, size=min(len(events), 4), replace=False) if events else []:
        sel = (df.survey == "TESS") & (np.abs(df.t_mjd - t) < 3 * width)
        df.loc[sel, "mag"] += depth * np.exp(-0.5 * ((df.loc[sel, "t_mjd"] - t - 0.05) / width) ** 2)
        planted.append(float(t))
    return df, planted


def build_packet(src: CaseStore, dest: Path, packet_id: str, cutoff: float | None, salt: dict | None = None) -> dict:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    out = CaseStore(dest)
    frames = {s: src.series(s) for s in src.surveys()}
    t0 = float(min(f.t_mjd.min() for f in frames.values() if not f.empty))
    pseud: dict = {}
    planted: list = []
    if salt and salt.get("kind") == "tess_dump_dips" and "tess" in frames:
        desat = [x for sec in src.context().get("tess", {}).get("sectors", {}).values() for x in sec.get("desat_mjd", [])]
        frames["tess"], planted = salt_tess_dumps(frames["tess"], desat, salt.get("depth", 0.01),
                                                  salt.get("width_days", 0.25), np.random.default_rng(salt.get("seed", 1)))
    for s, f in frames.items():
        g = scrub_series(f, t0, cutoff, pseud)
        if not g.empty:
            out.write_series(s, g)
    ctx = src.context()
    gaia = {k: v for k, v in (ctx.get("gaia") or {}).items() if k in KEEP_GAIA}
    nctx = {"gaia": gaia,
            "neighbors": [{k: n.get(k) for k in KEEP_NEIGHBOR} for n in ctx.get("neighbors", [])],
            "gaia_variability": {k: v for k, v in (ctx.get("gaia_variability") or {}).items()
                                 if k in ("summary",)}}
    if "tess" in ctx:
        secs = {}
        for i, (_k, v) in enumerate(sorted(ctx["tess"].get("sectors", {}).items(), key=lambda kv: int(kv[0]))):
            secs[f"{chr(97 + i)}"] = {"crowdsap": v.get("crowdsap"), "exptime": v.get("exptime"),
                                      "desat_mjd": [x - t0 for x in v.get("desat_mjd", [])]}
        nctx["tess"] = {"sectors": secs}
    out.write_context(nctx)
    prov = {}
    for k, v in src.provenance().items():
        prov[k] = {"archive": v.get("archive"), "rows_raw": v.get("rows_raw"), "rows_kept": v.get("rows_kept"),
                   "cuts": v.get("cuts", []), "status": v.get("status")}
    out.write_provenance(prov)
    summary = ("Identity, coordinates and calendar dates are hidden; times are days since the first observation. "
               "Observers are pseudonymous. Gaia DR3 context is the 2014-2017 mean.")
    if cutoff is not None:
        summary += (f" HINDSIGHT: data stop at day {cutoff - t0:.0f}. Register predictions (register_prediction) "
                    "about later times; they will be graded against what actually happened.")
    out.save(Case(id=packet_id, title=f"Trial star {packet_id}", summary=summary, status="observation"))
    return {"t0": t0, "cutoff_rel": (cutoff - t0) if cutoff else None, "planted_mjd": planted}


def build(spec_path: Path) -> dict:
    spec_path = Path(spec_path)
    trial = spec_path.parent
    spec = yaml.safe_load(spec_path.read_text())
    answers = {"trial": spec["name"], "salt": secrets.token_hex(16), "classes": list(CLASSES), "packets": {}}
    built = []
    for p in spec["packets"]:
        src = CaseStore.find(p["case"])
        info = build_packet(src, trial / "packets" / p["id"], p["id"], p.get("cutoff_mjd"), p.get("salt"))
        answers["packets"][p["id"]] = {"case": p["case"], "truth": p["truth"], "t0_mjd": info["t0"],
                                       "cutoff_mjd": p.get("cutoff_mjd"), "why": p.get("why", "")}
        if p.get("salt"):
            answers["packets"][p["id"]]["salt"] = {**p["salt"], "planted_mjd": info["planted_mjd"]}
        built.append({"packet": p["id"], "mode": "hindsight" if p.get("cutoff_mjd") else "blind"})
    (trial / "sealed").mkdir(exist_ok=True)
    (trial / "sealed" / "answers.yaml").write_text(yaml.safe_dump(answers, sort_keys=False))
    h = seal(trial)
    (trial / "manifest.json").write_text(json.dumps({
        "trial": spec["name"], "description": spec.get("description", ""), "answers_sha256": h,
        "classes": CLASSES, "packets": built}, indent=2))
    return {"trial": spec["name"], "answers_sha256": h, "packets": built}
