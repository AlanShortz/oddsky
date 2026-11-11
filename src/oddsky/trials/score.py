"""Score an investigator's runs against revealed answers. The scorecard is committed, failures included."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import yaml

from ..case.model import CLASSES, Check, now
from ..case.store import CaseStore
from ..tools import Toolbox, evaluate
from .seal import verify


def class_probs(hyps) -> dict[str, float]:
    p: dict[str, float] = {}
    for h in hyps:
        if h.status == "rejected":
            continue
        p[h.klass] = max(p.get(h.klass, 0.0), float(h.confidence or 0.0))
    tot = sum(p.values())
    if tot <= 0:
        return {}
    return {k: v / tot for k, v in sorted(p.items(), key=lambda kv: -kv[1])}


def score(trial: Path, agent: str, answers_path: Path | None = None) -> dict:
    trial = Path(trial)
    answers_path = answers_path or trial / "revealed" / "answers.yaml"
    if answers_path == trial / "revealed" / "answers.yaml" and not verify(trial):
        raise RuntimeError("revealed answers do not match the sealed commitment")
    answers = yaml.safe_load(Path(answers_path).read_text())
    runs = trial / "runs" / agent
    manifest = json.loads((trial / "manifest.json").read_text())
    # Score against the classes the investigators were offered when the trial was sealed.
    classes = list(manifest.get("classes") or CLASSES)
    cases, preds = [], []
    for pid, ans in answers["packets"].items():
        d = runs / pid
        if not (d / "case.yaml").exists():
            continue
        c = CaseStore(d).load()
        probs = class_probs(c.hypotheses)
        ranked = [{"klass": k, "p": round(v, 3)} for k, v in probs.items()]
        truth = ans.get("truth")
        top = [r["klass"] for r in ranked]
        entry = {"case": pid, "truth": truth, "ranked": ranked[:5]}
        if truth is None:
            # An open question: nobody knows the class, so the ranking is recorded but not scored.
            entry |= {"top1": None, "top2": None, "brier": None, "p_truth": None, "open_question": True}
        else:
            # Probability put on a class outside the trial's list counts as error, like any wrong class.
            y = {k: float(k == truth) for k in set(classes) | set(probs)}
            brier = float(sum((probs.get(k, 0.0) - y[k]) ** 2 for k in y))
            entry |= {"top1": top[:1] == [truth], "top2": truth in top[:2], "brier": round(brier, 3),
                      "p_truth": round(probs.get(truth, 0.0), 3)}
        entry |= {"n_claims": len(c.claims), "claims_by_tag": _tags(c.claims),
                  "mode": "hindsight" if ans.get("cutoff_mjd") else "blind", "real_case": ans["case"]}
        if ans.get("truth_source"):
            entry["truth_source"] = ans["truth_source"]
        cases.append(entry)
        if ans.get("cutoff_mjd"):
            full = Toolbox(author="scorer").store(ans["case"])
            tb = Toolbox()
            for p in c.predictions:
                if not p.check:
                    continue
                # Map relative trial days back onto the real calendar.
                chk = Check(**{**p.check.model_dump(), "start": p.check.start + ans["t0_mjd"],
                               "end": p.check.end + ans["t0_mjd"],
                               "baseline": (tuple(x + ans["t0_mjd"] for x in p.check.baseline)
                                            if p.check.baseline else None)})
                # The packet states its cutoff to the whole day, so a window opening on "the cutoff day" can start
                # a fraction of a day early. That is still a forecast: grade it from the cutoff on.
                if ans["cutoff_mjd"] - 1.0 <= chk.start < ans["cutoff_mjd"]:
                    chk = chk.model_copy(update={"start": float(ans["cutoff_mjd"])})
                if chk.start < ans["cutoff_mjd"]:
                    res_note = "window starts before the cutoff (not a prediction)"
                    preds.append({"case": pid, "id": p.id, "statement": p.statement, "probability": p.probability,
                                  "outcome": "invalid", "note": res_note})
                    continue
                frame = tb._frame(full, chk.series)
                # Pending means the sky has not got there yet. A survey that simply ended (ASAS-SN V in 2018)
                # will never fill the window, so those are graded on what exists, usually "unresolvable".
                latest = max(float(full.series(s).t_mjd.max()) for s in full.surveys())
                if frame.t_mjd.max() < chk.end and chk.end > latest:
                    preds.append({"case": pid, "id": p.id, "statement": p.statement, "probability": p.probability,
                                  "outcome": "pending", "note": f"window closes at MJD {chk.end:.0f}; data end "
                                  f"{frame.t_mjd.max():.0f}. Will be graded when the sky gets there."})
                    continue
                r = evaluate(chk, lambda ser, _s=full, _tb=tb: _tb._frame(_s, ser, grading=True))
                o = {"true": 1.0, "false": 0.0}.get(r.outcome)
                preds.append({"case": pid, "id": p.id, "statement": p.statement, "probability": p.probability,
                              "outcome": r.outcome, "observed": r.observed, "n_points": r.n_points,
                              "brier": round((p.probability - o) ** 2, 3) if o is not None else None,
                              "note": r.note})
    meta = yaml.safe_load((runs / "agent.yaml").read_text()) if (runs / "agent.yaml").exists() else {}
    rec = meta.get("recognised", {}) or {}
    for c in cases:
        c["recognised"] = str(rec.get(c["case"], "unknown"))
    n_packets = len(cases)
    cases_all, cases = cases, [c for c in cases if c["truth"] is not None]
    blind = [c for c in cases if c["recognised"] in ("no", "False")]
    resolved = [p for p in preds if p.get("brier") is not None]
    summary = {
        "n": len(cases),
        "n_packets": n_packets,
        "n_open_questions": n_packets - len(cases),
        "top1": round(float(np.mean([c["top1"] for c in cases])), 3) if cases else None,
        "top2": round(float(np.mean([c["top2"] for c in cases])), 3) if cases else None,
        "brier": round(float(np.mean([c["brier"] for c in cases])), 3) if cases else None,
        "mean_p_truth": round(float(np.mean([c["p_truth"] for c in cases])), 3) if cases else None,
        "predictions": len(preds),
        "predictions_resolved": len(resolved),
        "predictions_true": sum(p["outcome"] == "true" for p in resolved),
        "prediction_brier": round(float(np.mean([p["brier"] for p in resolved])), 3) if resolved else None,
        "n_unrecognised": len(blind),
        "top1_unrecognised": round(float(np.mean([c["top1"] for c in blind])), 3) if blind else None,
        "contamination_note": "self-reported: did the investigator think it recognised the star? Famous stars leak "
                              "through blinding; scores on unrecognised packets are the cleaner measure.",
        "baseline_note": f"uniform guessing over {len(classes)} classes: top1 {1 / len(classes):.3f}, "
                         f"brier {1 - 1 / len(classes):.3f}",
    }
    card = {"grader": "v2 (extremes = nightly medians)", "trial": answers["trial"], "agent": meta.get("agent", agent), "agent_meta": meta, "run_at": meta.get("run_at"),
            "scored_at": now(), "answers_sha256": manifest["answers_sha256"], "summary": summary,
            "cases": cases_all, "predictions": preds}
    (trial / "results").mkdir(exist_ok=True)
    (trial / "results" / f"{agent}.json").write_text(json.dumps(card, indent=2))
    return card


def _tags(claims) -> dict:
    out: dict[str, int] = {}
    for c in claims:
        out[c.tag] = out.get(c.tag, 0) + 1
    return out
