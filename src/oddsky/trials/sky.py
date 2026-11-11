"""What the sky did next: the held-back data behind each hindsight packet, with every forecast drawn on it.

Built from the same frames the grader reads, so the picture and the verdicts cannot disagree."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import yaml

from ..analysis import stats
from ..case.store import CaseStore
from ..tools import Toolbox

HISTORY = 2.5  # how much of the past to show, in units of the forecast horizon
MAX_POINTS = 700


def _threshold(chk, frame) -> float | None:
    """The magnitude a forecast put its line at, or None when it has no single line (amplitudes)."""
    if chk.statistic == "amplitude":
        return None
    if not chk.baseline:
        return float(chk.value)
    b = frame[(frame.t_mjd >= chk.baseline[0]) & (frame.t_mjd <= chk.baseline[1])].mag.to_numpy(float)
    return float(np.median(b) + chk.value) if len(b) >= 3 else None


def packet_sky(trial: Path, pid: str, ans: dict, agents: list[str], outcomes: dict) -> dict | None:
    t0, cutoff = ans["t0_mjd"], ans["cutoff_mjd"]
    full = Toolbox(author="scorer").store(ans["case"])
    tb = Toolbox()
    frames: dict = {}

    def frame(series: str):
        if series not in frames:
            frames[series] = tb._frame(full, series, grading=True)
        return frames[series]

    forecasts = []
    for agent in agents:
        d = trial / "runs" / agent / pid
        if not (d / "case.yaml").exists():
            continue
        for p in CaseStore(d).load().predictions:
            if not p.check:
                continue
            c = p.check
            abs_chk = c.model_copy(update={"start": c.start + t0, "end": c.end + t0,
                                           "baseline": tuple(x + t0 for x in c.baseline) if c.baseline else None})
            try:
                thr = _threshold(abs_chk, frame(c.series))
            except (ValueError, FileNotFoundError):
                thr = None
            o = outcomes.get((agent, pid, p.id), {})
            forecasts.append({"agent": agent, "id": p.id, "series": c.series, "start": round(abs_chk.start, 2),
                              "end": round(abs_chk.end, 2), "statistic": c.statistic, "op": c.op,
                              "value": c.value, "relative": bool(c.baseline),
                              "threshold": round(thr, 3) if thr is not None else None,
                              "probability": p.probability, "outcome": o.get("outcome"),
                              "observed": o.get("observed")})
    if not forecasts:
        return None
    # Draw the series most forecasts were about; the others are listed but not drawn.
    primary = Counter(f["series"] for f in forecasts).most_common(1)[0][0]
    for f in forecasts:  # the grader's rule: a window opening on the cutoff day starts at the cutoff
        if cutoff - 1.0 <= f["start"] < cutoff:
            f["start"] = cutoff
    drawn = [f for f in forecasts if f["series"] == primary and f["start"] >= cutoff]
    last = max((f["end"] for f in drawn), default=cutoff + 100)
    df = frame(primary)
    last = min(last, float(df.t_mjd.max()))
    horizon = max(last - cutoff, 30.0)
    lo, hi = cutoff - HISTORY * horizon, last + 0.06 * horizon
    win = df[(df.t_mjd >= lo) & (df.t_mjd <= hi)]
    nightly = stats.daily_bins(win, 1.0)
    if len(nightly) > MAX_POINTS:  # dense amateur series: coarser bins keep the shape and the file small
        nightly = stats.daily_bins(win, float(np.ceil((hi - lo) / MAX_POINTS)))
    return {"real_case": ans["case"], "cutoff_mjd": cutoff, "series": primary,
            "window": [round(max(lo, float(df.t_mjd.min())), 2), round(hi, 2)],
            "t": np.round(nightly.t_mjd.to_numpy(float), 2).tolist(),
            "mag": np.round(nightly.mag.to_numpy(float), 3).tolist(),
            "forecasts": forecasts}


def trial_payload(trial: Path) -> dict:
    """Everything the Trials page needs beyond the scorecards: the premise, the revealed key, the sky's answers."""
    trial = Path(trial)
    manifest = json.loads((trial / "manifest.json").read_text())
    out = {"trial": manifest["trial"], "title": manifest.get("title", ""), "description": manifest.get("description", ""),
           "answers_sha256": manifest.get("answers_sha256"), "n_classes": len(manifest.get("classes") or []),
           "packets": {p["packet"]: {"mode": p["mode"]} for p in manifest.get("packets", [])}}
    revealed = trial / "revealed" / "answers.yaml"
    if not revealed.exists():
        return out
    answers = yaml.safe_load(revealed.read_text())
    agents, outcomes = [], {}
    for f in sorted((trial / "results").glob("*.json")) if (trial / "results").exists() else []:
        card = json.loads(f.read_text())
        agents.append(f.stem)
        for p in card.get("predictions", []):
            outcomes[(f.stem, p["case"], p["id"])] = p
    for pid, ans in answers["packets"].items():
        info = out["packets"].setdefault(pid, {})
        info |= {"case": ans["case"], "truth": ans.get("truth"), "why": ans.get("why", ""),
                 "truth_source": ans.get("truth_source")}
        if ans.get("cutoff_mjd"):
            info["cutoff_mjd"] = ans["cutoff_mjd"]
            sky = packet_sky(trial, pid, ans, agents, outcomes)
            if sky:
                info["sky"] = sky
    return out
