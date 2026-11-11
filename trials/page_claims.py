"""Receipts for the sentences on the Trials page: `uv run oddsky paper-check trials/page_claims.py`.
Every number in trials/page.json is recomputed from the committed scorecards, run records and manifests."""
import json
from datetime import date
from pathlib import Path

import yaml

DOCUMENT = "page.json"
HERE = Path(__file__).resolve().parent
MODELS = {"Haiku": "claude-haiku-5.5", "Opus": "claude-opus-5.5", "Fable": "claude-fable-5.2"}
LIST_TOOLS = ("lens_fit", "eclipse_period")


def card(trial, model):
    return json.loads((HERE / f"strange-stars-{trial}" / "results" / f"{MODELS[model]}.json").read_text())


def recognised(c):
    return str(c["recognised"]).lower() not in ("no", "false", "none", "")


def build(c):
    t1 = {m: card("001", m) for m in MODELS}
    t2 = {m: card("002", m) for m in MODELS}
    scored = {m: [x for x in t2[m]["cases"] if x["truth"] is not None] for m in MODELS}
    graded = {m: [p for p in t2[m]["predictions"] if p["outcome"] in ("true", "false")] for m in MODELS}
    lost = {m: [p for p in t2[m]["predictions"] if p["outcome"] not in ("true", "false")] for m in MODELS}
    came_true = {m: sum(p["outcome"] == "true" for p in graded[m]) for m in MODELS}
    manifest = json.loads((HERE / "strange-stars-002" / "manifest.json").read_text())

    # what the two trials say together
    famous = [x["case"] for x in t1["Opus"]["cases"] if x["truth"] not in ("normal", "artifact_instrumental")]
    c.every("all eight packets that held a famous star",
            [len(famous) == 8] + [recognised(x) for m in ("Opus", "Fable") for x in t1[m]["cases"] if x["case"] in famous])
    c.every("both matched our answer on all five scored packets",
            [sum(x["top1"] for x in scored[m]) == 5 == len(scored[m]) for m in ("Opus", "Fable")])
    c.number("two of five", sum(x["top1"] for x in scored["Haiku"]))
    c.number("five (it had", len(scored["Haiku"]))
    c.number("five of ten in Trial 001", sum(x["top1"] for x in t1["Haiku"]["cases"]))
    c.number("ten in Trial 001", len(t1["Haiku"]["cases"]))
    c.number("scored 0.17", t2["Fable"]["summary"]["prediction_brier"])
    c.number("0.23 and Haiku", t2["Opus"]["summary"]["prediction_brier"])
    c.number("0.25. Each model", t2["Haiku"]["summary"]["prediction_brier"])
    c.ignore("always saying 50% earns 0.25", "arithmetic: (0.5 - outcome)^2")

    # Trial 002
    c.number("Eight packets", len(manifest["packets"]))
    c.number("three models", len(t2))
    c.number("Five scored packets", len(scored["Fable"]))
    c.number("For the five scored packets", len(scored["Opus"]))
    c.span("seven to fifteen gradable forecasts", [len(v) for v in graded.values()])
    c.number("Five of Fable’s fifteen", sum(p.get("n_points") == 3 for p in graded["Fable"]))
    c.number("fifteen were graded", len(graded["Fable"]))
    c.ignore("minimum of three measurements", "the grader's rule (tools.evaluate)")
    h03 = [p for p in graded["Fable"] if p["case"] == "H03"]
    c.number("three come from the packet", len(h03))
    c.number("11 of 12", came_true["Fable"] - sum(p["outcome"] == "true" for p in h03))
    c.number("12 came true", len(graded["Fable"]) - len(h03))
    c.number("its three graded forecasts", len(h03))
    c.number("two true, one false", sum(p["outcome"] == "true" for p in h03))
    answers = yaml.safe_load((HERE / "strange-stars-002" / "revealed" / "answers.yaml").read_text())["packets"]
    keyed = {k: v for k, v in answers.items() if v["truth"] is not None}
    c.number("four are our conclusions", sum(v["truth"] != "normal" for v in keyed.values()))
    c.number("two of them reproduced in a second survey", sum("second survey" in v.get("truth_source", "") for v in keyed.values()))
    c.number("three models under test", len(t2))
    cases = HERE.parent / "cases"
    c.every("worked on all four of those cases",
            ["claude-opus-5.5" in (cases / v["case"] / "case.yaml").read_text() for v in keyed.values() if v["truth"] != "normal"])
    c.ignore("all four of those cases", "the four conclusions counted in the sentence before")
    c.number("Eleven forecasts could not be graded", sum(len(v) for v in lost.values()))
    c.every("Haiku and Opus lost five forecasts each", [len(lost[m]) == 5 for m in ("Haiku", "Opus")])
    c.every("and Fable one: part", [len(lost["Fable"]) == 1])
    c.ignore("three measurements in a window", "the grader's rule (tools.evaluate)")
    ended = [(m, p["case"], p["id"]) for m in MODELS for p in lost[m] if p.get("n_points") == 0 and "ASAS" in p["statement"]]
    c.number("these three (Haiku H04 P2, Opus H04 P3 and P4)", len(ended))
    c.every("Haiku H04 P2, Opus H04 P3 and P4", [set(ended) == {("Haiku", "H04", "P2"), ("Opus", "H04", "P3"), ("Opus", "H04", "P4")}])
    c.external("Four verdicts changed in all", "re-scoring before and after the two rule changes in src/oddsky/trials/score.py; recomputed independently in trials/page_review.md")
    c.ignore("Two grader rules", "counts the two changes described in the same paragraph")
    used = {m: {d.name for d in (HERE / "strange-stars-002" / "runs" / MODELS[m]).iterdir() if (d / "ledger.jsonl").exists()
                and any(json.loads(line)["tool"] in LIST_TOOLS for line in (d / "ledger.jsonl").read_text().splitlines())}
            for m in MODELS}
    c.number("four packets and Fable", len(used["Opus"]))
    c.number("three; Haiku", len(used["Fable"]))
    c.every("Haiku’s record shows neither tool run on any star", [not used["Haiku"]])
    c.ignore("two tools", "lens_fit and eclipse_period")
    lens = [k for k, v in keyed.items() if v["truth"] == "microlensing"]
    c.every("It still named both lensing events", [len(lens) == 2] + [x["top1"] for x in scored["Haiku"] if x["case"] in lens])
    c.number("of its three misses", sum(not x["top1"] for x in scored["Haiku"]))
    c.external("about two minutes in", "ledger timestamps of runs/claude-fable-5.2: first call to last call before the gap")
    c.external("Two of its packets were finished", "ledger timestamps: T02 and T04 end before the gap (checked in trials/page_review.md)")
    c.ignore("H03 P1", "packet and forecast id")

    # Trial 001
    days = (date.fromisoformat(t1["Fable"]["run_at"]) - date.fromisoformat(t1["Opus"]["run_at"])).days
    c.number("Fable ran two weeks later", days / 7)
    c.number("Fable ran two weeks after the others", days / 7)
    c.number("Ten packets", len(t1["Fable"]["cases"]))
    c.every("the first two models ran", [len(t1) - 1 == 2])
    c.every("the tools the first two used", [len(t1) - 1 == 2])
    c.number("famous stars and two controls", len(t1["Opus"]["cases"]) - len(famous))

    c.ignore("Trial 001", "trial name")
    c.ignore("strange-stars-001", "trial name")
    c.ignore("strange-stars-002", "trial name")
    c.ignore("Fable 5.2", "model name")
    c.ignore("Opus 5.5", "model name")
    c.ignore("Haiku 5.5", "model name")
    c.ignore("H03", "packet id")
    c.ignore("H04", "packet id")
    for pid in ("T01", "T02", "T03", "T04", "H01"):
        c.ignore(pid, "packet id")
    c.ignore("two larger models", "Opus and Fable")
    c.ignore("two trials", "the two trials on the page")
    c.ignore("other two", "Haiku and Opus")
    c.ignore("one contestant", "Opus 5.5")
    c.review("page_review.md")
