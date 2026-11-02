"""Open case OS-0030: an apparently unreported infrared transient in NGC 3239 (Arp 263), found blind by hunt H-0012's
difference imaging and confirmed by HST and JWST archival images (hunts/H-0012/reviews/claude-referee-triage-2026-11-01.md and
the independent check hunts/H-0012/reviews/ngc3239-check-2026-11-01.md). Not a star with survey light curves, so no archive fetch:
the evidence is the H-0012 difference photometry and the HST/JWST measurements recorded below.

    uv run python scripts/open_case_30.py
"""

import shutil
from pathlib import Path

from oddsky.case.store import CaseStore
from oddsky.fetch import open_case
from oddsky.tools import Toolbox

CHK = "hunts/H-0012/reviews/ngc3239-check-2026-11-01.md"
REF = "hunts/H-0012/reviews/claude-referee-triage-2026-11-01.md"
store = open_case("NGC 3239 IR transient 2020", ra=156.291224, dec=17.163778, hunt="H-0012",
                  title="An infrared flare in the galaxy NGC 3239 in 2020 that no optical survey saw: an obscured transient",
                  hook="Found blind by Oddsky's mid-infrared difference imaging of 318 nearby galaxies (hunt H-0012): a flare peaking in "
                       "2020 November at about 5e5 L_sun, with no optical alert. Hubble caught a faint point source 85 days after the "
                       "peak that has since vanished, and JWST found cooling dust at the same spot in 2024.")
cid = store.path.name
tb = Toolbox(mode="open", author="claude-opus-5.5")
claims = [
    ("WISE (unWISE neo11 epochal coadds, difference imaging): flat from 2010 to 2020 May 2; on 2020 Nov 23 W1 +232 +- 8 and W2 +308 +- 20 "
     "uJy above the 2010-11 level; 91/119 uJy in 2021 Apr, 38/42 in 2021 Nov, ~27 in 2022 Apr. Position 156.29118 +17.16387 (Gaia-tied, "
     f"~0.25\"). Positive in both visit seasons, so not an asteroid ({CHK}).", "observed"),
    ("The transient's W1-W2 is 0.95 +- 0.08 (~960 K dust); a blackbody gives ~5.6e5 L_sun at 7.9 Mpc (1.6-2.4x more at the 10-12 Mpc "
     "of SN 2012A's host distance and CosmicFlows-4). The rise is unresolved (< 205 d), so the true peak may be higher.", "computed"),
    ("HST (2021 Feb 16): a point source at 156.291224 +17.163778, 0.37\" from the WISE centroid, F606W 25.93 +- 0.06 and F814W 24.95 +- 0.06 "
     "AB, present in all four 2021 exposures; absent in 2022 (F606W > 27.1) and in every 2025 filter, with no residual cluster (M_V > -2.9). "
     "The chance of an unrelated vanishing source within 0.37\" is ~0.2%.", "observed"),
    ("JWST (programme 3707, 2024 Apr-May): a new unresolved source 0.01\" from the HST position, F335M 5.9 uJy and F300M 3.2-3.6 uJy, "
     "nothing in F150W (> 26.5 AB): ~580 K dust at ~3.6e4 L_sun. Spitzer 2008 shows nothing there (> 8 sigma below the 2024 source).",
     "observed"),
    ("No optical detection: no TNS object or ZTF alert; ATLAS limits o ~20.4-21.7 around the event; the galaxy was in solar conjunction "
     "in 2020 August. VLASS < 0.36 mJy (2021 Nov); Chandra 2025 < 2.6e37 erg/s.", "observed"),
    ("Not a buried normal supernova as it stands: the HST colour allows A_V <~ 2, while the faintness relative to WISE needs A_V 9-20, "
     "and an enshrouded Type II SN should be 30-100x brighter in the infrared at this phase. An obscured luminous red nova (stellar "
     "merger), an ILRT-like eruption (no progenitor seen), or a low-energy SN behind clumpy dust fit better. Not an AGN: 2.7 kpc from the "
     "centre of a galaxy with no nucleus.", "inferred"),
    ("Not reported (2026-11-01): TNS, Gaia alerts, CBAT, ATel (web search), SPIRITS, MIRONG, the literature; no publication on the JWST 3707 "
     "data at this position. ADS full-text check of the De et al. WISE transient papers still owed.", "observed"),
]
ids = [tb.add_claim(cid, t, g, [])["claim"] for t, g in claims]
tb.add_hypothesis(cid, "eruptive", "A dust-obscured stellar eruption or merger (luminous red nova or ILRT-like event) in NGC 3239, "
                  "peaking around 2020 November.", supports=[ids[i] for i in (0, 1, 2, 3, 5)],
                  would_falsify="A JWST spectrum showing supernova signatures, or a late radio detection of a normal SN.", confidence=0.55)
tb.add_hypothesis(cid, "dust_formation", "A low-energy or heavily, clumpily obscured core-collapse supernova whose dust is now cooling.",
                  supports=[ids[i] for i in (0, 1, 3)], would_falsify="A spectrum of the remnant without supernova features.",
                  confidence=0.35)
a = tb.add_hypothesis(cid, "artifact_instrumental", "A WISE, HST or JWST artifact, or an unrelated variable star.",
                      conflicts=[ids[0], ids[2], ids[3]], would_falsify="Already falsified by three instruments at one position.",
                      confidence=0.02)["hypothesis"]
tb.update_hypothesis(cid, a, "rejected", reason="WISE, HST and JWST see the same unreported object at one position")
fig = store.path / "figures"
fig.mkdir(exist_ok=True)
for f in ("summary.png", "hst_stamps.png", "jwst_stamps.png", "wise_lc.png"):
    shutil.copy(Path("hunts/H-0012/reviews/ngc3239-check-2026-11-01") / f, fig / f)
c = CaseStore(store.path).load()
c.status = "reproduced"
c.summary = ("A mid-infrared flare in the irregular galaxy NGC 3239 (about 8-12 Mpc), peaking in 2020 November at roughly 5e5 L_sun from "
             "~960 K dust, that no optical survey reported. Hubble caught a faint, fading point source 85 days after the peak, and JWST "
             "found cooling dust at the same spot in 2024. Probably a dust-obscured stellar merger or eruption; a buried low-energy "
             "supernova is possible. Found blind by Oddsky hunt H-0012.")
CaseStore(store.path).save(c)
print(cid, ids)
