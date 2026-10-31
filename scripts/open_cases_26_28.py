"""Open cases for the three strongest refereed lens candidates without one: J172057 and J180402 (H-0009; Gaia DR3 epoch
photometry confirms both) and J175634 (H-0008; ATLAS). Records claims from the referee reports, a microlensing hypothesis and the
status. No predictions: J172057 and J180402 peaked inside Gaia DR3's span, so DR4 cannot test them blind; J175634's one Gaia transit
at its peak is a DR5 matter.

    uv run python scripts/open_cases_26_28.py
"""

from __future__ import annotations

from pathlib import Path

from oddsky import skeptic
from oddsky.case.store import CaseStore
from oddsky.data import atlas
from oddsky.data.provenance import Provenance
from oddsky.fetch import fetch, open_case
from oddsky.tools import Toolbox

R9 = "hunts/H-0009/reviews/claude-referee-atlas-2026-10-31.md"
R8 = "hunts/H-0008/reviews/claude-referee-atlas10b-2026-10-31.md"
TARGETS = {
    "J172057": dict(
        gaia="5959812622743175552", ra=260.23771063651, dec=-41.70021713832, hunt="H-0009", status="reproduced", p=0.65,
        atlas=("hunts/H-0009/work/atlas/atlas_J172057.txt", "5274895"),
        title="A star in Scorpius brightened sixfold in 2015, seen by NEOWISE and Gaia: an apparently unreported microlensing candidate",
        hook="Found blind in Oddsky hunts H-0008/H-0009 (NEOWISE x4.5 on 2015 Sep 7). Gaia DR3 epoch photometry shows the same event, "
             "x5.9 seven days earlier and fading over six weeks, equal in BP and RP. Gaia's own classifier labels the star MICROLENSING.",
        claims=[
            ("NEOWISE on 2015 Sep 7: x4.5 in W1 and x4.8 in W2 against the star's median; every other visit quiet. Found blind by "
             "hunts H-0008/H-0009.", "observed"),
            ("Gaia DR3 epoch photometry of Gaia DR3 5959812622743175552 (G 17.9): G x5.87 on 2015 Aug 30 (7 d before the NEOWISE visit), "
             "x2.71 at +25 d and x1.76 at +44 d, with BP and RP rising equally. No other brightening in Gaia's 2014-2017 record "
             f"({R9}).", "observed"),
            ("The event is on Gaia DR3 5959812622743175552, 0.59\" from the NEOWISE position, not on the star first matched at 2.2\" "
             "(which has no epoch photometry): the NEOWISE centroid shifts toward it during the event.", "computed"),
            ("The Gaia DR3 classifier (vari_classifier_result) labels the star MICROLENSING (score 0.60); it is not in the Gaia DR3 "
             "microlensing catalogue (vari_microlensing).", "observed"),
            ("Not in TNS, the Gaia alerts, the KMTNet, OGLE or ZTF lists, VSX, SIMBAD or a web search (2026-10-31). MOA and the KMTNet "
             "2015 season are unchecked. ATLAS did not cover the event (its data start 193 d later).", "observed")],
        hyp="A lens magnified the Gaia star about six times in late August 2015 (P 0.65, H-0009 ATLAS referee)."),
    "J180402": dict(
        gaia="4143495279954502016", ra=271.00958351919, dec=-18.31329775461, hunt="H-0009", status="reproduced", p=0.60,
        atlas=("hunts/H-0009/work/atlas/atlas_J180402.txt", "5274900"),
        title="A star in Sagittarius brightened 2.6 times in September 2015, equally in Gaia and NEOWISE: a microlensing candidate",
        hook="Found blind in Oddsky hunts H-0008/H-0009 (NEOWISE x2.7 on 2015 Sep 15). Gaia DR3 epoch photometry shows x2.6 nine days "
             "earlier and twenty days later, equal in G and RP. Gaia's own classifier labels the star MICROLENSING.",
        claims=[
            ("NEOWISE on 2015 Sep 15: x2.7 in W1 and x2.75 in W2 against the star's median; every other visit quiet.", "observed"),
            (f"Gaia DR3 epoch photometry: G x2.60 at -9 d and x2.57 at +20 d, RP the same ({R9}).", "observed"),
            ("The Gaia DR3 classifier labels the star MICROLENSING (score 0.26); it is not in the Gaia DR3 microlensing catalogue.",
             "observed"),
            ("ATLAS's 2015 images at this position are too blurred (PSF 4 px) to measure the event.", "computed")],
        hyp="A lens magnified the star about 2.6 times around 2015 September (P 0.60, H-0009 ATLAS referee)."),
    "J175634": dict(
        gaia="4070998667212085888", ra=269.1431574054454, dec=-20.93253611105695, hunt="H-0008", status="reproduced", p=0.75,
        atlas=("hunts/H-0008/work/atlas/atlas_J175634.txt", "5273742"),
        title="A star in Sagittarius brightened briefly in March 2022 while OGLE was paused: a short microlensing candidate",
        hook="Found blind in Oddsky hunt H-0008 (NEOWISE x2.2 on 2022 Mar 19). ATLAS shows a sharp, symmetric event peaking on "
             "2022 Mar 25 and lasting about two weeks, the same in optical and infrared. OGLE was paused and the star is outside "
             "KMTNet's fields.",
        claims=[
            ("NEOWISE on 2022 Mar 19: x2.22 in W1 and x2.31 in W2, on the rise a few days before the ATLAS peak, matching ATLAS o (x2.25) at that "
             f"time ({R8}).", "observed"),
            ("ATLAS (task 5273742, four units, both bands) shows one event in 2015-2026: t0 2022 Mar 25.0 +- 0.5 d, tE about 10-14 d, "
             "u0 0.08-0.15, source flux share about 1 in ATLAS c, o and NEOWISE W1, W2. The peak fell in a 4-day gap, so the maximum "
             "(x7-14) was not observed. A static lens beats a free symmetric bump by delta chi2 16-23.", "computed"),
            ("OGLE was paused from 2020 Mar 18 to 2022 Aug 12; the star is in an OGLE-IV field but just outside KMTNet's BLG38. Gaia "
             "passed on 2022 Mar 25 00:11 UT, at the peak, without an alert; only DR5 will show it.", "observed"),
            ("Not in TNS, the Gaia alerts, the KMTNet, OGLE or ZTF lists, VSX, SIMBAD or a web search. MOA 2022 unchecked.", "observed")],
        hyp="A short microlensing event, tE 10-14 d, peaking 2022 Mar 25 (P 0.75, H-0008 ATLAS referee)."),
}


def main() -> None:
    tb = Toolbox(mode="open", author="claude-opus-5.5")
    for key, t in TARGETS.items():
        store = open_case(f"Gaia DR3 {t['gaia']}", title=t["title"], hook=t["hook"], ra=t["ra"], dec=t["dec"], hunt=t["hunt"])
        cid = store.path.name
        print(key, cid, flush=True)
        print(fetch(store, ["gaia", "gaia_epoch", "neowise", "neowise_exp"]), flush=True)
        path, task = t["atlas"]
        raw = atlas.parse(Path(path).read_text())
        df = atlas.to_series(raw, chi_max=1e9)
        store.write_series("atlas", df)
        prov = store.provenance()
        p = Provenance(archive="ATLAS forced photometry (fallingstar-data.com), reduced images",
                       query={"ra": t["ra"], "dec": t["dec"], "use_reduced": True, "task": task})
        p.rows_raw, p.rows_kept = len(raw), int((df.flag == "").sum())
        p.notes += [f"reused the hunt's server response {path}", "chi_n cut disabled: chi_n rises with flux"]
        prov["atlas"] = p.model_dump()
        store.write_provenance(prov)
        ids = [tb.add_claim(cid, text, tag, [])["claim"] for text, tag in t["claims"]]
        tb.add_hypothesis(cid, "microlensing", t["hyp"], supports=ids, would_falsify="A repeat brightening, or a colour change.",
                          confidence=t["p"])
        c = CaseStore(store.path).load()
        c.status = t["status"]
        CaseStore(store.path).save(c)
        print(skeptic.run(store)["summary"], flush=True)


if __name__ == "__main__":
    main()
