"""Open cases for the two real new objects of hunt H-0012's v2 rerun (h0012b), from the referee report
hunts/H-0012/reviews/claude-referee-h0012b-2026-11-02.md (with its literature addendum):

- NGC 2403 obs#50: periodic (P ~ 5.3 yr), dust-obscured mid-infrared outbursts with no optical counterpart.
- NGC 55 fsn#7: a luminous dusty source whose mid-infrared light faded threefold in 2010-2024 while its blue optical star stayed
  constant; not a failed supernova.

Neither is a star with survey light curves, so there is no archive fetch: the evidence is the H-0012 difference photometry and
the Spitzer/HST measurements recorded in the report. The NGC 2403 ephemeris (next peak ~2028.5) is recorded as a claim and as the
falsifier of the leading hypothesis; it is not a machine-checkable prediction, because no survey in the grader observes 3-5 um
after NEOWISE (2024).

    uv run python scripts/open_cases_31_32.py
"""

import shutil
from pathlib import Path

from oddsky.case.store import CaseStore
from oddsky.fetch import open_case
from oddsky.tools import Toolbox

REF = "hunts/H-0012/reviews/claude-referee-h0012b-2026-11-02.md"
FIG = Path("hunts/H-0012/reviews/h0012b-referee")
tb = Toolbox(mode="open", author="claude-opus-5.5")


def finish(store, status, summary, figures):
    fig = store.path / "figures"
    fig.mkdir(exist_ok=True)
    for f in figures:
        shutil.copy(FIG / f, fig / f)
    c = CaseStore(store.path).load()
    c.status = status
    c.summary = summary
    CaseStore(store.path).save(c)


# ---------------------------------------------------------------- NGC 2403 obs#50
s = open_case("NGC 2403 periodic IR source", ra=114.22807, dec=65.59806, hunt="H-0012",
              title="A hidden star in NGC 2403 that throws off dust every 5.3 years: four infrared outbursts, 2007-2023",
              hook="Found blind by Oddsky's mid-infrared difference imaging of nearby galaxies (hunt H-0012 v2): a source invisible to "
                   "Hubble that brightens in the infrared every 5.3 years. Spitzer saw outbursts in 2007, 2012 and 2018, WISE in 2017-18 "
                   "and 2023. Probably a massive binary forming dust at each close approach. The next outburst is due around mid-2028.")
cid = s.path.name
claims = [
    ("WISE (unWISE neo11 epochal coadds, difference imaging): two humps in both bands and both visit seasons, peaking 2017.8 "
     "(W1 +170, W2 +355 uJy) and 2023.2 (W2 +300 uJy), with a flat minimum between; compact PSF at 8-9 sigma in the per-epoch "
     f"difference stamps. 21\" from the nucleus of NGC 2403 ({REF}, section 1).", "observed"),
    ("Spitzer/IRAC (about 40 epochs, 2004-2019; aperture photometry on resampled mosaics): [4.5] peaks of +235, +232 and +243 uJy "
     "at 2007.25, 2012.45 and 2018.03, with flat minima between; fast rise (2006.2 to 2006.8), slower 1-1.5 yr decline; [3.6] "
     "tracks at about 60% of the amplitude. The Spitzer variable is 0.23-0.25\" from the WISE position.", "observed"),
    ("Four peaks (2007.25, 2012.45, 2017.5-2018.0, 2023.2) give a period of 5.3 +- 0.1 yr (about 1,940 d); the ephemeris "
     "predicts the next peak at about 2028.5. Hump light W1-W2 ~ 1.4 (about 700 K dust), peak nu L_nu about 5-7e4 L_sun per "
     "band at 3.2 Mpc.", "computed"),
    ("No optical counterpart: HST (ACS 2004/2005/2019, WFC3 2018, WFC3/IR 2010) shows a dust lane, with the nearest faint "
     "sources 0.68\" and 0.96\" away (M_I fainter than about -4.5); no Gaia source within 4.6\"; no ZTF alert object within 5\".",
     "observed"),
    ("Not reported (2026-11-02): ADS full text for the coordinates; not SPIRITS 19q (2.7' away) or SPIRITS 16df (1.5' away), "
     "the known dust-forming WC binaries in NGC 2403; not [KSK2013] N 2403 5 (5.6\" away); nothing within 3\" in the SPIRITS, "
     "Khan et al. 2013/2015, Gaia DR3 or AllWISE catalogues; nothing in TNS within 50\" or in the SPIRITS long-period-variable "
     "catalogue within 10\".", "observed"),
]
ids = [tb.add_claim(cid, t, g, [])["claim"] for t, g in claims]
tb.add_hypothesis(cid, "dust_formation", "A colliding-wind massive binary (WC + O, or an LBV binary) forming dust at each "
                  "periastron every 5.3 yr, about 10x more luminous in the infrared than WR 140.", supports=ids[:4],
                  would_falsify="No mid-infrared brightening between 2027.8 and 2029.3, or an infrared spectrum with silicate or "
                                "SiC features (AGB dust) instead of a featureless carbon-dust continuum.", confidence=0.7)
tb.add_hypothesis(cid, "pulsation", "An extreme AGB / OH-IR star with a 1,940-day pulsation.", supports=[ids[0]],
                  conflicts=[ids[1], ids[2]],
                  would_falsify="Already strained: periods above 1,900 d are extremely rare, Miras do not show a fast rise and "
                                "flat minimum, and 7e4 L_sun in one band exceeds an AGB star's total output.", confidence=0.15)
tb.add_hypothesis(cid, "artifact_instrumental", "A WISE or Spitzer artefact.", conflicts=[ids[0], ids[1]],
                  would_falsify="Two observatories see the same periodic source at one position, and the 2017-18 peak is "
                                "seen by both.", confidence=0.02)
finish(s, "reproduced",
       "An optically invisible source in NGC 2403 (3.2 Mpc) whose mid-infrared light rises sharply every 5.3 years and then "
       "settles: Spitzer caught outbursts in 2007, 2012 and 2018, and WISE in 2017-18 and 2023. Each outburst is about 1e5 "
       "L_sun of ~700 K dust. Most likely a massive binary forming dust at each close approach, like WR 140 but about ten times "
       "brighter in the infrared. Next outburst expected around 2028.5. Found blind by Oddsky hunt H-0012.",
       ["lead_NGC2403_obs50.png", "epochs_NGC2403_obs50.png", "spitzer_ngc2403.png", "hst_ngc2403.png"])
print(cid, ids)

# ---------------------------------------------------------------- NGC 55 fsn#7
s = open_case("NGC 55 fading dusty star", ra=3.80788, dec=-39.2148, hunt="H-0012",
              title="A luminous star in NGC 55 lost two-thirds of its infrared glow in 2010-2024 while staying the same in visible light",
              hook="Found by Oddsky's failed-supernova search (hunt H-0012 v2), but not a failed supernova: the mid-infrared light "
                   "faded threefold over 14 years while Hubble shows the blue, luminous star unchanged. Its dust is clearing.")
cid = s.path.name
claims = [
    ("WISE (unWISE neo11, absolute PSF flux): a smooth, decelerating fade with no recovery, W1 740 to 251 uJy and W2 1,675 to "
     "456 uJy from 2010.4 to 2024.4 (var_sig 14.4); the faded light has W1-W2 ~ 1.6 (650-700 K dust) and the fractions lost are "
     f"similar (66% and 73%). nu L_nu in 2010: 9e4 (W1) and 1.6e5 L_sun (W2) at 2.13 Mpc ({REF}, section 2).", "observed"),
    ("Spitzer 2005: [4.5] = 1,727 uJy, equal to W2 in mid-2010 within 3%, so the source was steady for 4.5 yr before fading; "
     "the IRAC SED rises to 8 um (L_IR >~ 3e5 L_sun in 2005-10).", "observed"),
    ("Optical counterpart Gaia DR3 4997972666905659392, 0.20\" away: G = 20.18, BP-RP = 0.14. HST F814W 21.20 (2007) and "
     "21.10 (2024): constant to ~0.1 mag while the mid-infrared fell threefold. M_V ~ -6.7, an OB supergiant-class luminosity.",
     "observed"),
    ("Not reported: no ADS full-text match for the coordinates; nothing in SIMBAD within 4\" or TNS within 30\"; NGC 55 was "
     "not observed by SPIRITS.", "observed"),
]
ids = [tb.add_claim(cid, t, g, [])["claim"] for t, g in claims]
tb.add_hypothesis(cid, "dust_formation", "A dusty massive star (sgB[e], LBV or WR dust-maker) whose circumstellar dust, in a "
                  "disk or a shell seen through a gap, is dissipating after an earlier dust-forming episode.", supports=ids,
                  would_falsify="An optical spectrum showing a quasar redshift, or no B[e]/LBV/WR emission lines.",
                  confidence=0.7)
tb.add_hypothesis(cid, "artifact_blend", "A background AGN behind NGC 55, coincident with the blue star.", supports=[ids[1]],
                  conflicts=[ids[2]],
                  would_falsify="A stellar optical spectrum at NGC 55's velocity; the blue point source steady to 0.1 mag for 17 "
                                "years and ~700 K dust (not 1,200-1,500 K) already disfavour it.", confidence=0.2)
finish(s, "reproduced",
       "A luminous, blue star in the nearby galaxy NGC 55 (2.1 Mpc) whose mid-infrared light was steady from 2005 to 2010 and "
       "then faded threefold by 2024, while Hubble shows the star itself unchanged. Most likely a massive star's dust disk or "
       "shell dissipating. It is also a warning case for failed-supernova searches: an infrared 'vanishing' source that is not "
       "a vanishing star. Found by Oddsky hunt H-0012.",
       ["lead_NGC55_fsn7.png", "epochs_NGC55_fsn7.png", "hst_ngc55.png", "spitzer_ngc55.png"])
print(cid, ids)
