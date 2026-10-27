"""Build the web viewer's development fixtures from the real export. Standard library only.

    python3 web/dev/make_fixtures.py

Reads web/data/index.json and web/data/cases/OS-0001.json (written by `oddsky export-web`), copies
the real data and adds a plausible sample argument (claims, hypotheses, predictions, skeptic,
ledger, investigation) so the argument UI can be developed before the real one exists. Numbers in
the sample claims are computed from the real light curves, but the argument itself is SAMPLE TEXT:
load it only with ?fixture=1.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import statistics as st
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]
CASE_ID = "OS-0001"


def mjd(iso: str) -> float:
    return (dt.datetime.fromisoformat(iso) - dt.datetime(1858, 11, 17)).total_seconds() / 86400


def iso_of(m: float) -> str:
    return (dt.datetime(1858, 11, 17) + dt.timedelta(days=m)).date().isoformat()


def window(ser: dict, a: float, b: float) -> list[float]:
    return [v for t, v in zip(ser["t"], ser["mag"]) if a <= t <= b]


def digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:16]


def build_case(real: dict) -> dict:
    d = json.loads(json.dumps(real))
    S = d["series"]
    V, B, I = S["AAVSO:V"], S["AAVSO:B"], S["AAVSO:I"]
    W1, W2 = S["NEOWISE:W1"], S["NEOWISE:W2"]
    y25 = (mjd("2025-01-01"), mjd("2025-12-31"))
    medV25, medB25, medI25 = (st.median(window(x, *y25)) for x in (V, B, I))
    fV, fB, fI = max(V["mag"]), max(B["mag"]), max(I["mag"])
    tV = V["t"][V["mag"].index(fV)]
    # the IR jump: last visit before 2018 vs first after
    j = next(i for i, t in enumerate(W1["t"]) if t > mjd("2018-01-01"))
    dW1, dW2 = W1["mag"][j - 1] - W1["mag"][j], W2["mag"][j - 1] - W2["mag"][j]
    col = [a - b for a, b in zip(W1["mag"], W2["mag"])]
    pre = st.median(col[:j])
    peak = max(col)
    lead = (V["t"][0] - W1["t"][j]) / 365.25
    ratio = (fB - medB25) / (fI - medI25)
    g = d["context"]["gaia"]
    nb = [n for n in d["context"].get("neighbors", []) if n["sep_arcsec"] <= 6.1]
    worst = max(nb, key=lambda n: n["flux_ratio_G"]) if nb else None
    observer = next((n.split(":", 1)[1].strip() for n in d["provenance"]["aavso"]["notes"] if n.startswith("observers")), "")

    who = "claude-opus-5.5 (sample)"
    at = "2026-10-27T09:00:00+00:00"
    ledger_specs = [
        ("K1", "gaia_context", {"target": "ASASSN-21qj", "radius_arcsec": 30}),
        ("K2", "neowise_lightcurve", {"target": "ASASSN-21qj", "radius_arcsec": 3.0, "cuts": "default"}),
        ("K3", "aavso_lightcurve", {"target": "ASASSN-21qj", "bands": ["B", "V", "R", "I"]}),
        ("K4", "color_trend", {"case": CASE_ID, "a": "NEOWISE:W1", "b": "NEOWISE:W2", "pair_within_days": 1.0}),
        ("K5", "find_dips", {"case": CASE_ID, "series": "AAVSO:V", "baseline_days": 600, "min_depth": 0.1}),
        ("K6", "neighbors", {"target": "ASASSN-21qj", "radius_arcsec": 30, "max_dG": 8}),
        ("K7", "skeptic_report", {"case": CASE_ID}),
    ]
    d["ledger"] = [{"id": k, "tool": t, "args": a, "digest": digest([k, t, a]), "author": who, "at": at} for k, t, a in ledger_specs]

    # a few flagged points so the "show flagged points" toggle can be exercised
    V["flagged"] = {"n": 6, "t": [59460.4, 59501.3, 59720.2, 60110.5, 60540.4, 60812.1],
                    "mag": [15.9, 16.6, 13.2, 14.1, 12.9, 13.95],
                    "why": ["discrepant (val=T)", "upper limit", "discrepant (val=T)", "visual estimate", "discrepant (val=T)", "upper limit"]}

    c = d["case"]
    c["featured"] = True
    c["hook"] = ("In 2018 this Sun-like star began to glow in the infrared. Three years later it nearly vanished "
                 "in visible light. What happened in between?")
    c["summary"] = (
        f"ASASSN-21qj is an ordinary-looking star {g['distance_pc']:.0f} pc away, about as luminous as the Sun. "
        f"NEOWISE saw its 4.6 µm brightness jump by {dW2:.2f} mag in early 2018 while its optical light stayed put. "
        f"In 2021 the optical light collapsed: V fell to {fV:.1f}, nearly {fV - medV25:.1f} mag below where it sits today. "
        "The order of events, warm dust first and shadow later, is the puzzle. *This argument is sample fixture text.*"
    )
    c["claims"] = [
        {"id": "C1", "tag": "observed", "calls": ["K2"], "author": who, "at": at,
         "text": f"NEOWISE W2 brightened by {dW2:.2f} mag and W1 by {dW1:.2f} mag between the visits of {iso_of(W1['t'][j - 1])[:7]} and {iso_of(W1['t'][j])[:7]}, after four years flat to within 0.04 mag."},
        {"id": "C2", "tag": "observed", "calls": ["K3", "K5"], "author": who, "at": at,
         "text": f"AAVSO V reached {fV:.2f} mag on {iso_of(tV)}, {fV - medV25:.2f} mag fainter than its 2025 median of {medV25:.2f}; B and I dimmed at the same time."},
        {"id": "C3", "tag": "computed", "calls": ["K4"], "author": who, "at": at,
         "text": f"W1 − W2 went from {pre:+.2f} before 2018 to {peak:+.2f} at the infrared peak, then relaxed to {col[-1]:+.2f} by 2024: a temporary excess of warm dust, a few hundred to ~1000 K."},
        {"id": "C4", "tag": "computed", "calls": ["K5"], "author": who, "at": at,
         "text": f"At minimum the dimming was {fB - medB25:.2f} mag in B but {fI - medI25:.2f} mag in I (ΔB/ΔI = {ratio:.2f}), closer to small interstellar-like grains (≈2.2) than to grey, large-grain dust (≈1)."},
        {"id": "C5", "tag": "computed", "calls": ["K1"], "author": who, "at": at,
         "text": f"Gaia DR3 gives G = {g['G']:.2f}, Teff ≈ {g['teff_gspphot']:.0f} K, d = {g['distance_pc']:.0f} pc, M_G = {g['abs_G']:.2f} and RUWE = {g['ruwe']:.2f}: a Sun-like main-sequence star with no astrometric sign of a close companion."},
        {"id": "C6", "tag": "inferred", "calls": ["K2", "K3"], "author": who, "at": at,
         "text": f"The infrared rise came at least {lead:.1f} years before AAVSO's first optical measurement, which already caught the star {V['mag'][0] - medV25:.1f} mag faint. The warm material existed before anything crossed our line of sight."},
        {"id": "C7", "tag": "inferred", "calls": ["K6", "K2"], "author": who, "at": at,
         "text": (f"A neighbour is an unlikely culprit: the only Gaia source inside the 6.1″ WISE beam sits {worst['sep_arcsec']:.1f}″ away with {worst['flux_ratio_G']:.1%} of the target's G flux; "
                  "even allowing for its red colour it would have to brighten roughly tenfold in W2.") if worst else "No Gaia neighbour falls inside the WISE beam."},
        {"id": "C8", "tag": "speculated", "calls": [], "author": who, "at": at,
         "text": "Warm dust first, then a long shadow, is what a giant impact between two planets would look like: a hot, expanding debris cloud that later drifts across the face of the star."},
    ]
    c["hypotheses"] = [
        {"id": "H1", "klass": "collision_debris", "status": "favored", "confidence": 0.55, "author": who,
         "statement": "A collision between planetary bodies made a hot debris cloud (the 2018 infrared glow) that later passed in front of the star (the 2021–22 dimming).",
         "supports": ["C1", "C3", "C6", "C8"], "conflicts": [],
         "would_falsify": "Infrared and optical changes that repeat on a regular period, or a W1 − W2 colour excess too blue for dust that is cooling as it expands."},
        {"id": "H2", "klass": "dust_occultation", "status": "live", "confidence": 0.25, "author": who,
         "statement": "A long-lived dusty structure on a wide orbit (a clump or a warped disk) occults the star once per orbit; its warm face rotated into view first.",
         "supports": ["C2", "C4"], "conflicts": ["C3"],
         "would_falsify": "No second dimming within a decade, and no infrared excess before 2018 in archival WISE (2010) data."},
        {"id": "H3", "klass": "yso_dipper", "status": "disfavored", "confidence": 0.08, "author": who,
         "statement": "A young star whose inner disk throws variable shadows.",
         "supports": ["C2"], "conflicts": ["C3", "C5"],
         "would_falsify": "Already strained: there was no infrared excess before 2018, and the star sits on the main sequence."},
        {"id": "H4", "klass": "artifact_blend", "status": "rejected", "confidence": 0.02, "author": who,
         "statement": "The neighbour at 3.8″ is the real variable and contaminates the target's photometry.",
         "supports": [], "conflicts": ["C2", "C7"],
         "would_falsify": "Rejected on arithmetic: a neighbour with 3.8% of the target's flux could dim the blend by at most 0.04 mag even if it vanished, not 2.7."},
    ]
    p_res = window(V, mjd("2026-01-01"), mjd("2026-06-30"))
    obs = st.median(p_res) - medV25
    c["predictions"] = [
        {"id": "P1", "hypothesis": "H1", "author": "the advisor (sample)", "registered_at": "2025-06-01T12:00:00+00:00", "resolve_by": "2026-07-31",
         "statement": "The debris has cleared: in early 2026 the star will be no more than 0.1 mag fainter than in 2025.",
         "probability": 0.75,
         "check": {"series": "AAVSO:V", "start": mjd("2026-01-01"), "end": mjd("2026-06-30"), "statistic": "median", "baseline": list(y25), "op": "<", "value": 0.1},
         "resolution": {"outcome": "true" if obs < 0.1 else "false", "observed": round(obs, 3), "n_points": len(p_res), "resolved_at": "2026-07-02T08:00:00+00:00",
                        "note": "The star is holding at its recovered brightness."}},
        {"id": "P2", "hypothesis": "H1", "author": who, "registered_at": at, "resolve_by": "2027-07-31",
         "statement": "If this was a one-off collision, the star stays steady: the first-half 2027 V median will be within 0.3 mag of 2025.",
         "probability": 0.7,
         "check": {"series": "AAVSO:V", "start": mjd("2027-01-01"), "end": mjd("2027-06-30"), "statistic": "median", "baseline": list(y25), "op": "<", "value": 0.3}},
        {"id": "P3", "hypothesis": "H2", "author": who, "registered_at": at, "resolve_by": "2028-01-31",
         "statement": "If an orbiting clump did it, a new dimming will begin: B will swing by more than 0.5 mag during 2027.",
         "probability": 0.15,
         "check": {"series": "AAVSO:B", "start": mjd("2027-01-01"), "end": mjd("2027-12-31"), "statistic": "amplitude", "op": ">", "value": 0.5}},
    ]
    c["literature"] = [{"bibcode": "2023Natur.622..251K", "note": "Kenworthy et al.: a planetary collision afterglow and transit of the resultant debris cloud."}]

    cuts = d["provenance"]["neowise"]["cuts"]
    removed = {}
    for cut in cuts:
        band, rest = cut.split(":", 1)
        removed[band] = removed.get(band, 0) + int(rest.rsplit(" ", 1)[-1])
    raw = d["provenance"]["neowise"]["rows_raw"]
    w = max(removed.values())
    d["skeptic"] = {
        "generated_at": at, "version": "0.1.0",
        "summary": "Two warnings to read before believing anything: every optical point comes from one observer, and the start of the dimming was never seen.",
        "checks": [
            {"id": "blend_neowise", "title": "Neighbours inside the NEOWISE beam (6.1\")", "status": "warn",
             "finding": f"1 Gaia source(s) within 6.1\"; brightest contributes {worst['flux_ratio_G']:.1%} of the target's G flux at {worst['sep_arcsec']:.1f}\"; 1 is much redder than the target and may matter more in the infrared",
             "numbers": {"radius_arcsec": 6.1, "n_inside": 1, "brightest_flux_ratio": worst["flux_ratio_G"], "brightest_sep": worst["sep_arcsec"]}},
            {"id": "blend_aavso", "title": "Neighbours inside the AAVSO beam (5.0\")", "status": "warn",
             "finding": f"1 Gaia source(s) within 5.0\"; brightest contributes {worst['flux_ratio_G']:.1%} of the target's G flux at {worst['sep_arcsec']:.1f}\"",
             "numbers": {"radius_arcsec": 5.0, "n_inside": 1, "brightest_flux_ratio": worst["flux_ratio_G"]}},
            {"id": "wise_saturation", "title": "WISE saturation", "status": "pass", "finding": "all visits fainter than the W1/W2 saturation limits", "numbers": {"saturated_visits": 0}},
            {"id": "wise_cuts", "title": "NEOWISE single-exposure quality cuts", "status": "pass",
             "finding": f"{raw} exposures; cuts removed up to {w} ({w / raw:.0%}) per band; 0 visits kept with fewer than 3 exposures",
             "numbers": {"exposures": raw, "removed_per_band": removed, "thin_visits": 0}},
            {"id": "confirmation", "title": "Independent optical confirmation", "status": "warn",
             "finding": f"optical data from 1 independent source(s): AAVSO observer {observer.replace(':', ' (')}). One instrument or observer is a single point of failure; seek a second.",
             "numbers": {"sources": {f"AAVSO observer {observer.split(':')[0]}": int(observer.split(':')[1])}}},
            {"id": "chromatic", "title": "Multi-band consistency of the main event", "status": "pass",
             "finding": f"deepest V event at MJD {tV:.0f}: change vs. out-of-event median per band B {fB - medB25:+.2f}, V {fV - medV25:+.2f}, I {fI - medI25:+.2f}; dB/dI = {ratio:.2f} (ISM-like dust ~2.2, grey dust ~1)",
             "numbers": {"deltas": {"B": round(fB - medB25, 3), "V": round(fV - medV25, 3), "I": round(fI - medI25, 3)}}},
            {"id": "onset_aavso_V", "title": "Was the start seen? (AAVSO V)", "status": "warn",
             "finding": f"the {fV - medV25:.2f}-mag dip peaking at MJD {tV:.0f} begins at the edge of the data or right after a gap; its true start and shape are unobserved",
             "numbers": {"event": {"peak_mjd": round(tV, 2), "depth_mag": round(fV - medV25, 3), "starts_after_gap": True}}},
            {"id": "alias_aavso_V", "title": "Periodicity vs survey rhythms (AAVSO V)", "status": "pass",
             "finding": "strongest period 9.33 d is not a known survey/Earth rhythm (not yet evidence it is real)",
             "numbers": {"top_period_days": 9.33, "power": 0.081}},
            {"id": "tess_crowdsap", "title": "TESS aperture contamination (CROWDSAP)", "status": "skip", "finding": "no TESS light curve fetched for this case", "numbers": {}},
        ],
    }
    d["investigations"] = [{"file": "claude-2026-10-27.md", "markdown": INVESTIGATION.format(
        dW2=dW2, pre=pre, peak=peak, fV=fV, fV_minus=fV - medV25, ratio=ratio, lead=lead)}]
    return d


INVESTIGATION = """# The glow came first

*Sample investigation (fixture text) by claude-opus-5.5, run through Claude Code with the Oddsky MCP tools.*

## What I did

1. Ran the **Skeptic** before looking at anything else. Two warnings matter: one optical observer, and an unobserved onset.
2. Pulled NEOWISE and paired W1/W2 visits taken within a day (`color_trend`, receipt K4).
3. Measured the depth of the optical event per band (`find_dips`, receipt K5).

## What the data says

| quantity | value | tag |
|---|---:|---|
| W2 jump, 2017 → 2018 | {dW2:.2f} mag | observed |
| W1 − W2 before / at peak | {pre:+.2f} / {peak:+.2f} | computed |
| deepest V (vs. 2025 median) | {fV:.2f} (+{fV_minus:.2f}) | observed |
| ΔB / ΔI at minimum | {ratio:.2f} | computed |

The infrared rise leads the optical record by at least **{lead:.1f} years**. That ordering is the whole case:
something got *warm* before it got *in the way*.

## What would change my mind

- A second W2 rise with no matching optical event later.
- Any sign of periodicity in the optical dips (the 9.3 d peak is unconvincing).
- A second observer's light curve that disagrees with HMB's.

## Next

```
oddsky predict OS-0001 --series AAVSO:V --window 2027-01-01:2027-06-30 \\
    --statistic median --baseline 2025 --op "<" --value 0.3 --p 0.7
```

See also [Kenworthy et al. 2023](https://ui.adsabs.harvard.edu/abs/2023Natur.622..251K/abstract).
"""


def build_index(real_index: dict, case: dict) -> dict:
    idx = json.loads(json.dumps(real_index))
    c = case["case"]
    for e in idx["cases"]:
        if e["id"] == c["id"]:
            e.update(hook=c["hook"], featured=True, n_claims=len(c["claims"]), n_hypotheses=len(c["hypotheses"]), n_predictions=len(c["predictions"]))
    idx["scorecards"] = json.loads((WEB / "dev" / "fixture-scorecards.json").read_text())["scorecards"]
    return idx


if __name__ == "__main__":
    real = json.loads((WEB / "data" / "cases" / f"{CASE_ID}.json").read_text())
    case = build_case(real)
    (WEB / "dev" / f"fixture-{CASE_ID}.json").write_text(json.dumps(case, separators=(",", ":")))
    real_index = json.loads((WEB / "data" / "index.json").read_text())
    (WEB / "dev" / "fixture-index.json").write_text(json.dumps(build_index(real_index, case), indent=1))
    print(f"wrote dev/fixture-{CASE_ID}.json and dev/fixture-index.json")
