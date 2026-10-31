"""OS-0020..OS-0025: claims, hypotheses, the six refereed Gaia DR4 predictions (hunts/H-0009/predictions/dr4_referee.md, exact
statements S1a-S6b, Checks unchanged from dr4_proposal.json) and statuses. One prediction per case: the referee dropped the
seven correlated ones so the ledger records six bets, not thirteen."""

from oddsky.case.store import CaseStore
from oddsky.tools import Toolbox

tb = Toolbox(mode="open", author="claude-opus-5.5")
REF_A10 = "hunts/H-0008/reviews/claude-referee-atlas10-2026-10-30.md"
REF_DR4 = "hunts/H-0009/predictions/dr4_referee.md"
CASES = {
    "OS-0020": dict(status="reproduced", p=0.75, claims=[
        ("NEOWISE on 2017 Aug 17: x8 brighter in both W1 and W2 than the star's 2014-2024 median; every other visit quiet. Found "
         "blind by hunt H-0008.", "observed"),
        ("ATLAS (task 5273734) shows one smooth brightening in 2016-2026, peaking at x6-9 in mid-August 2017 and back to normal by "
         f"early 2018. A point lens fits only with annual parallax (piE ~0.38 in every reduction); tE ~120-190 d ({REF_A10}).",
         "computed"),
        ("Gaia scanned the star 19 d before, 3 d after and 33 d after the ATLAS peak and issued no alert; Gaia alerted on only 5 of "
         f"12 comparable DR3 lenses, so the missing alert is weak evidence ({REF_DR4}).", "computed"),
        ("Not in TNS, the Gaia alerts, the KMTNet, OGLE or ZTF microlensing lists, or a web search (2026-10-30). MOA and ASAS-SN "
         "not checked.", "observed")],
        hyp="A foreground lens magnified the star for about four months in 2017 (P 0.75, ATLAS-follow-up referee).",
        pred=("Gaia DR4 G epoch photometry of Gaia DR3 6020322385418675200 (or the DR4 source cross-matched to it): the median G of "
              "the transits in MJD 57949-58042 (2017-07-15 to 2017-10-16 00:00; forecast 6 transits on Jul 29, Aug 20 and Sep 19) "
              "is more than 1.2 mag brighter than the median G in MJD 56863.5-57570 (2014-07-25 to 2016-07-01). Model: 1.6-2.1 mag.",
              0.93, 57949, 58042, "median", 56863.5, 57570, -1.2)),
    "OS-0021": dict(status="reproduced", p=0.55, claims=[
        ("NEOWISE: x1.4 on 2018 Mar 16 and x3.0 on 2018 Aug 27, equal in W1 and W2; every other visit quiet. Found blind by hunt "
         "H-0008.", "observed"),
        ("ATLAS (task 5273739) shows one smooth x7.7 brightening peaking 2018 Jul 11-14. A static lens needs a source brighter than "
         "all the light in the aperture and is excluded; a lens fits only with annual parallax, and tE is unconstrained (~120-490 "
         f"d). The rise is mildly chromatic and the peak may be partly saturated ({REF_A10}).", "computed"),
        ("Gaia scanned the star 27, 50 and 80 d after the ATLAS peak without an alert.", "computed")],
        hyp="A long microlensing event with annual parallax (P 0.55, ATLAS-follow-up referee); not established.",
        pred=("Gaia DR4 G epoch photometry of Gaia DR3 5952322268527918208 (or the DR4 source cross-matched to it): the brightest "
              "nightly-median G in MJD 58150-58400 (2018-02-01 to 2018-10-09 00:00; forecast 10 transits on 6 nights) is more than "
              "1.0 mag brighter than the median G in MJD 56863.5-57935 (2014-07-25 to 2017-07-01). Model: 1.4-1.85 mag, on 2018 Aug 9.",
              0.90, 58150, 58400, "brightest", 56863.5, 57935, -1.0)),
    "OS-0022": dict(status="observation", p=None, claims=[
        ("NEOWISE on 2018 Jul 14: x6.9 brighter in both W1 and W2 (2.10 and 2.12 mag) than the star's median; every other visit "
         "quiet. No optical survey covered the event. Found blind by hunts H-0008/H-0009.", "observed")],
        hyp=None,
        pred=("Gaia DR4 G epoch photometry of Gaia DR3 5862971688685406976 (or the DR4 source cross-matched to it): the median G of "
              "the transits in MJD 58255-58340 (2018-05-17 to 2018-08-10 00:00; forecast 6 transits on May 26, Jun 19 and Jul 27) is "
              "more than 0.15 mag brighter than the median G in MJD 56863.5-57935 (2014-07-25 to 2017-07-01). Tests: a weeks-to-months "
              "brightening of the Gaia star (lens, or slow non-lens outburst) against a short outburst, an artifact or an event on "
              "another star.", 0.50, 58255, 58340, "median", 56863.5, 57935, -0.15)),
    "OS-0023": dict(status="observation", p=None, claims=[
        ("NEOWISE: x1.8 on 2017 Mar 1 and x8.3 on 2017 Aug 15, equal in W1 and W2, quiet before and after. No optical survey "
         "covered the event. Found blind by hunt H-0009.", "observed")],
        hyp=None,
        pred=("Gaia DR4 G epoch photometry of Gaia DR3 5932843350525331968 (or the DR4 source cross-matched to it): the median G of "
              "the transits in MJD 57945-58025 (2017-07-11 to 2017-09-29 00:00; forecast 5 transits on Jul 23, Aug 17 and Sep 16) is "
              "more than 0.5 mag brighter than the median G in MJD 56863.5-57570 (2014-07-25 to 2016-07-01).",
              0.74, 57945, 58025, "median", 56863.5, 57570, -0.5)),
    "OS-0024": dict(status="observation", p=None, claims=[
        ("NEOWISE on 2015 Aug 1: x2.5 brighter in both W1 and W2 than the star's median; every other visit quiet. No optical survey "
         "covered the event. Found blind by hunts H-0008/H-0009.", "observed"),
        ("Gaia DR3 built this star's mean G from fewer CCD measurements than its neighbours (1.4th percentile) and shows high scatter, "
         f"which in 47 calibration lenses favours an event Gaia saw (likelihood ratio ~7; {REF_DR4}).", "computed")],
        hyp=None,
        pred=("Gaia DR4 G epoch photometry of Gaia DR3 5863586423081438848 (or the DR4 source cross-matched to it): the median G of "
              "the transits in MJD 57185-57300 (2015-06-12 to 2015-10-05 00:00; forecast 6 transits on 4 nights) is more than 0.2 mag "
              "brighter than the median G in MJD 57600-58868 (2016-07-31 to 2020-01-20). Tests: a months-long event on the Gaia star "
              "(lens or slow non-lens) against an artifact, a flare or an event on another star.",
              0.70, 57185, 57300, "median", 57600, 58868, -0.2)),
    "OS-0025": dict(status="observation", p=None, claims=[
        ("NEOWISE on 2017 Aug 12: x2.3 brighter in both W1 and W2 than the star's median; every other visit quiet. No optical survey "
         "covered the event. Found blind by hunts H-0008/H-0009.", "observed"),
        ("A Gaia G 17.6 neighbour 3.2\" away carries 73% of the target's G flux inside the NEOWISE beam, so the brightening may "
         "belong to it.", "observed")],
        hyp=None,
        pred=("Gaia DR4 G epoch photometry of Gaia DR3 5882495205642608896 (or the DR4 source cross-matched to it): the median G of "
              "the transits in MJD 57945-58020 (2017-07-11 to 2017-09-24 00:00; forecast 5 transits on Jul 21, Aug 17 and Sep 15) is "
              "more than 0.15 mag brighter than the median G in MJD 56863.5-57630 (2014-07-25 to 2016-08-30). Tests: a brightening of "
              "the Gaia star lasting more than ~2 weeks (lens or slow non-lens) against a short outburst, an artifact or an event on "
              "the G 17.6 neighbour.", 0.45, 57945, 58020, "median", 56863.5, 57630, -0.15)),
}
for cid, c in CASES.items():
    ids = [tb.add_claim(cid, text, tag, [])["claim"] for text, tag in c["claims"]]
    h = None
    if c["hyp"]:
        h = tb.add_hypothesis(cid, "microlensing", c["hyp"], supports=ids, would_falsify="Gaia DR4 flat during the event, or a repeat.",
                              confidence=c["p"])["hypothesis"]
    stmt, prob, a, b, stat, b0, b1, val = c["pred"]
    r = tb.register_prediction(cid, stmt, prob, "GAIA:G", a, b, "<", val, statistic=stat, baseline_start=b0, baseline_end=b1,
                               hypothesis=h, resolve_by="2027-12-31")
    s = CaseStore.find(cid)
    case = s.load()
    case.status = c["status"]
    s.save(case)
    print(cid, r["prediction"], r["check"])
