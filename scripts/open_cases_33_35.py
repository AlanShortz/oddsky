"""Open cases for the three real repeating sources from hunt H-0013 (hunts/H-0013/README.md, verdict table and referee section),
after an ADS full-text and SPIRITS-catalogue novelty check (2026-11-02):

- NGC 4945 #13: three mid-infrared cycles at P = 5.4 yr with a fast rise, no counterpart anywhere.
- NGC 3344 #6: WR 140-like outbursts about every 10 yr, 0.4" from an SDSS spectrum with Wolf-Rayet features.
- M81 #6: two large obscured outbursts at least 14 yr apart (by 2009.9, and 2023.9-2024.4).

The evidence is H-0012 difference photometry and H-0013's Spitzer IRAC light curves, so there is no archive fetch.

    uv run python scripts/open_cases_33_35.py
"""

import shutil
from pathlib import Path

from oddsky.case.store import CaseStore
from oddsky.fetch import open_case
from oddsky.tools import Toolbox

R13 = "hunts/H-0013/README.md"
FIG = Path("hunts/H-0013/figures")
LPV = ("Luminous dusty long-period variables reach P = 1,000-2,500 d and nu L_nu(4.5 um) of order 1e5-5e5 L_sun "
       "(Karambelkar et al. 2019, SPIRITS), so pulsation is not excluded by luminosity alone")
NOVEL = ("Not reported (2026-11-02): ADS full text for the coordinates and for the host with variability terms finds nothing on this "
         "source; nothing in TNS, SIMBAD, Gaia DR3, AllWISE or the Spitzer SEIP catalogue at the position; the SPIRITS catalogue of "
         "luminous long-period variables (Karambelkar et al. 2019) does not cover this galaxy.")
tb = Toolbox(mode="open", author="claude-opus-5.5")


def make(name, ra, dec, title, hook, claims, hyps, summary, figs):
    store = open_case(name, ra=ra, dec=dec, hunt="H-0013", title=title, hook=hook)
    cid = store.path.name
    ids = [tb.add_claim(cid, t, g, [])["claim"] for t, g in claims]
    for klass, statement, sup, con, fals, p in hyps:
        tb.add_hypothesis(cid, klass, statement, supports=[ids[i] for i in sup], conflicts=[ids[i] for i in con],
                          would_falsify=fals, confidence=p)
    fig = store.path / "figures"
    fig.mkdir(exist_ok=True)
    for f in figs:
        shutil.copy(FIG / f, fig / f)
    c = CaseStore(store.path).load()
    c.status = "reproduced"
    c.summary = summary
    CaseStore(store.path).save(c)
    print(cid, ids)


make("NGC 4945 periodic IR source", 196.41592, -49.42001,
     "A hidden source in NGC 4945 that has flared in the infrared every 5.4 years: three outbursts with a sudden rise",
     "Found blind by Oddsky's search for repeating infrared sources in nearby galaxies (hunt H-0013): WISE sees cycles peaking in "
     "2011, 2016-17 and 2022, and Spitzer caught the 2016 rise, a jump of 25x in under half a year. Nothing is catalogued at the "
     "position. Next peak expected around 2027.5.",
     [(f"WISE (unWISE neo11 difference photometry, H-0012/H-0013): three cycles peaking 2011.27, 2016.71 and 2022.14, a period of "
       f"5.43 yr (WISE) and 5.37 yr (joint WISE + Spitzer fit), with a sawtooth shape: fast rise (about 8% of the period), slower "
       f"decline, short minimum ({R13}).", "observed"),
      ("Spitzer/IRAC warm mission 2012-2019 tracks two cycles: from +22 to +505 (3.6 um) / +748 uJy (4.5 um) between 2016.34 and "
       "2016.78, a rise in under 0.45 yr; a single 2007.6 [4.5] epoch fits the decline of a 2005.9 cycle.", "observed"),
      ("Peak-to-trough W2 amplitude about 3e5 L_sun at 3.8 Mpc. The light-curve shape test favours a flat-minimum outburst train over a "
       f"sinusoid (Z_joint = +83). {LPV}.", "computed"),
      ("No optical or near-infrared counterpart: nothing in Gaia DR3 or HST at the position, in the dust lane of an edge-on starburst; "
       "a Galactic foreground star (b = +13 deg) is implausible with no Gaia source and P = 5.4 yr.", "observed"),
      (NOVEL, "observed")],
     [("dust_formation", "A massive colliding-wind binary forming dust at each periastron every 5.4 yr, deeply embedded in NGC 4945.",
       [0, 1, 2, 3], [], "An infrared spectrum with silicate or SiC features (AGB dust), or no brightening in 2026.8-2028.3.", 0.5),
      ("pulsation", "An extremely luminous dusty long-period variable (super-AGB star or red supergiant with extreme mass loss).",
       [0, 2], [1], "Already strained by the fast rise and flat minimum, which pulsators do not show.", 0.35),
      ("artifact_instrumental", "A WISE or Spitzer artefact.", [], [0, 1],
       "Two observatories see the same cycles at one position.", 0.03)],
     "An infrared source in the dusty edge-on starburst galaxy NGC 4945 (3.8 Mpc) that brightens sharply every 5.4 years: WISE "
     "saw cycles in 2011, 2016-17 and 2022, and Spitzer caught the 2016 rise. Each swing is about 3e5 L_sun, with no optical "
     "counterpart. Most likely a massive binary forming dust at each close approach; an extreme dusty pulsating star is the "
     "alternative. Next peak expected around 2027.5. Found blind by Oddsky hunt H-0013.",
     ["spitzer_NGC4945_1974m500_13.png"])

make("NGC 3344 periodic IR source", 160.88167, 24.96630,
     "A source in NGC 3344 next to Wolf-Rayet stars that flares in the infrared about every 10 years, like the dust maker WR 140",
     "Found blind by Oddsky's search for repeating infrared sources (hunt H-0013): sharp infrared outbursts in 2004, 2014 and 2023, "
     "each lasting about a year and a half over a flat minimum, on a young star cluster whose spectrum shows Wolf-Rayet features. "
     "Next outburst expected around 2033.",
     [(f"Spitzer/IRAC: +80 uJy above quiescence at 2004.32 in both bands; quiescent 2012.5-2013.1; a rise caught at 2013.18 and a peak "
       f"at 2014.1 (+85 uJy); quiescent again by 2016. WISE: flat 2016-2022, then a new outburst peaking about 2023.3 ({R13}).",
       "observed"),
      ("Outbursts spaced 9.8 and about 9.2 yr, each lasting about 1.5 yr (duty cycle about 0.15) with a fast rise: the morphology of "
       "WR 140. Peak nu L_nu(W2) about 1e5 L_sun at 6.85 Mpc, about 30x WR 140. The Spitzer variable is a point source 0.45\" from the "
       "WISE position.", "computed"),
      ("It lies 0.4\" from [BKD2008] WR 541, an SDSS fibre spectrum with Wolf-Rayet features (Brinchmann, Kunth & Durret 2008), on a "
       "blue knot (Gaia G = 21.1, BP-RP about 0, M_G about -8: a young cluster). The WR signature belongs to a 3\" (about 100 pc) "
       "fibre, not necessarily to this star.", "observed"),
      ("Caveat: the 2004 outburst rests on a single Spitzer epoch.", "observed"),
      (NOVEL, "observed")],
     [("dust_formation", "A WR 140-like colliding-wind Wolf-Rayet binary forming dust at each periastron, P about 10 yr.",
       [0, 1, 2], [], "No infrared outburst in 2031-2035, or an infrared spectrum showing silicate dust.", 0.55),
      ("pulsation", "An extremely luminous dusty long-period variable.", [0], [1],
       "A 10-yr period is well beyond the longest known pulsators (about 7 yr), and the flat minimum argues against it.", 0.15),
      ("artifact_blend", "Two unrelated events, or variability of another source in the cluster.", [3], [1],
       "A third well-sampled outburst at the predicted time.", 0.15)],
     "An infrared source in the spiral galaxy NGC 3344 (6.9 Mpc) that flares for about a year and a half roughly every 10 years "
     "(2004, 2014, 2023), on a young cluster whose spectrum shows Wolf-Rayet stars. It looks like a scaled-up WR 140, a binary "
     "that makes dust each time its stars swing close. Next outburst expected around 2033. Found blind by Oddsky hunt H-0013.",
     ["spitzer_NGC3344_1601p242_6.png"])

make("M81 recurrent IR outburst", 148.73908, 69.14676,
     "Two large infrared eruptions 14 years apart in an HII region of M81, the second in 2024",
     "Found by Oddsky's infrared searches of nearby galaxies (hunts H-0012 and H-0013): an obscured source in M81 erupted by 2009 "
     "and again in 2023-24, each time reaching about 3e5 L_sun in the infrared, with nothing seen between.",
     [(f"Spitzer: flat 2003.8-2005.0, then +196 uJy at 2009.9 declining to +98 uJy by 2010.4; WISE 2010 agrees ({R13}).", "observed"),
      ("WISE: flat 2014-2023, then a sharp rise in 2023.9-2024.4 to W1 0.75 / W2 1.0 mJy (about 3e5 L_sun at 3.6 Mpc). H-0012 v2 ranks "
       "it 8th among obscured transients (hunts/H-0012/work/triage_h0012b.csv).", "observed"),
      ("It sits on a giant molecular cloud / HII region next to a blue Gaia source (G = 20.25, BP-RP = 0.37, M_G about -7.5); the "
       "nearest TNS object is AT 2026dvq, 22.6\" away.", "observed"),
      (NOVEL.replace(" the SPIRITS catalogue of luminous long-period variables (Karambelkar et al. 2019) does not cover this galaxy.",
                     " nothing within 10\" in the SPIRITS catalogue of luminous long-period variables, which covers M81."),
       "observed")],
     [("eruptive", "Recurrent eruptions of a massive star (LBV-like), each forming or heating dust.", [0, 1, 2], [],
       "A post-2024 infrared decline with a supernova-like spectrum, or a third outburst inconsistent with one star.", 0.5),
      ("dust_formation", "A long-period (about 16 yr) dust-forming binary.", [0, 1], [],
       "No outburst near 2039-2040.", 0.25),
      ("artifact_blend", "Two unrelated transients in the same HII region.", [2], [], "Further outbursts from the same point.",
       0.15)],
     "An obscured source in an HII region of M81 (3.6 Mpc) that erupted in the infrared by 2009 and again in 2023-24, each time "
     "reaching about 3e5 L_sun, with nothing between. Probably recurrent eruptions of a massive star; a long-period dust maker "
     "or two unrelated events are possible. Post-2024 infrared data would tell. Found by Oddsky hunts H-0012 and H-0013.",
     ["spitzer_MESSIER081_1507p696_6.png"])
