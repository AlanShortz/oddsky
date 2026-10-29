"""OS-0016: record the claims, hypotheses and the Gaia DR4 prediction (cites call ids K1-K7 from the analysis calls)."""

from oddsky.tools import Toolbox

C = "OS-0016"
tb = Toolbox(mode="open", author="claude-opus-5.5")
ids = {}


def claim(key, text, tag, calls=None):
    ids[key] = tb.add_claim(C, text, tag, calls or [])["claim"]


claim("nw", "In the NEOWISE visit of 2017 Aug 27-28 (MJD 57992.6-57993.5) the star was 1.087 mag brighter in W1 (10.036 against a "
      "baseline median of 11.123) and 1.072 mag brighter in W2 (10.131 against 11.202): factors of 2.72 and 2.68, equal within "
      "0.02 mag. In the 13 single exposures the factors are 2.731 and 2.716 (hunts/H-0007).", "observed", ["K1", "K2"])
claim("flat", "Apart from that visit, NEOWISE W1 is flat over 21 visits (2014-2024) with a robust scatter of 0.007 mag.",
      "computed", ["K3"])
claim("atlas", "ATLAS o (2015 Oct - 2026 Oct, 2,911 frames) contains exactly one excursion beyond max(5 sigma, 0.2 mag): a "
      "brightening from MJD 57970.6 to 58063.5 (2017 Aug 5 - Nov 6) peaking on MJD 58009.6 (2017 Sep 13) at 2.13 mag (x7.1) above "
      "baseline. On the night of the NEOWISE visit ATLAS o was 1.13 mag (x2.8) above baseline.", "observed", ["K4", "K5"])
claim("ztf", "ZTF r (2018 Jul - 2025 Aug, 869 points) is flat with a robust scatter of 0.011 mag.", "computed", ["K6"])
claim("nb", "No Gaia DR3 source within 6\" contributes more than 0.6% of the target's G flux; the nearest comparable star (G = 15.9) "
      "is 15.3\" away, outside the NEOWISE beam.", "observed", ["K7"])
claim("fit", "A symmetric point-lens curve is rejected (chi2 462/69 against 98/67 with annual parallax) by a joint ATLAS + NEOWISE "
      "fit (scripts/hunt_h0007_lensfit.py, outside the Oddsky tools). The asymmetry appears in both ATLAS units and survives every "
      "systematics variant a referee tried. Parallax model: t0 = MJD 58012.2, tE = 47.7 or 51.8 d (u0 sign), A_max about 7; "
      "pi_E,par = 0.62 is robust, |piE| = 0.6-1.6 (hunts/H-0007/reviews/claude-referee-2-2026-10-29.md).", "computed")
claim("colour", "A hot additive source (flare, accretion disk) supplying 63% of the light during the NEOWISE visit would make W1-W2 "
      "redder by about 0.06 mag; the observed change is -0.01 to -0.02 mag. A flare of that size on a 33 Lsun giant is not physical.",
      "inferred", ["K1", "K2"])
claim("novel", "Not found (2026-10-29) in VSX (6\"), TNS (60\"), SIMBAD (CfA mirror, 30\"), the Gaia Science Alerts, Gaia DR3 "
      "vari_microlensing (which ends 2017 May) or a web search; no ATLAS17 designation. ADS not checked. Gaia observed the star on "
      "2017 Jul 27, Aug 22 and Sep 18 (one field of view) without alerting.", "observed")
claim("mass", "The lens mass is not measured: theta_E is unknown. Along the mass-distance relation the lens is 0.1-0.65 Msun at "
      "0.5 kpc or 0.04-0.26 Msun at 1 kpc, most likely an M dwarf within about 1 kpc.", "inferred")

h = tb.add_hypothesis(C, "microlensing", "A foreground star (probably an M dwarf within ~1 kpc) passed within ~0.14 Einstein radii "
                      "of the red-clump giant, magnifying it about sevenfold; the asymmetry is most likely annual parallax.",
                      supports=[ids[k] for k in ("nw", "flat", "atlas", "ztf", "fit", "colour")],
                      would_falsify="Gaia DR4 epoch photometry flat on 2017 Sep 18, or different BP and RP amplitudes; any repeat brightening.",
                      confidence=0.95)["hypothesis"]
e = tb.add_hypothesis(C, "eruptive", "An unseen companion (accreting white dwarf, flare star) had an outburst lasting about three months.",
                      conflicts=[ids["colour"], ids["fit"]], would_falsify="A colour change during the event, or a repeat.",
                      confidence=0.03)["hypothesis"]
a = tb.add_hypothesis(C, "artifact_instrumental", "A NEOWISE or ATLAS artifact.", conflicts=[ids["nw"], ids["atlas"]],
                      would_falsify="Already falsified: two independent instruments see the same event on the same night.",
                      confidence=0.01)["hypothesis"]
b = tb.add_hypothesis(C, "artifact_blend", "A neighbouring source brightened.", conflicts=[ids["nb"], ids["nw"]],
                      would_falsify="Already falsified: no neighbour within 6\" is brighter than 0.6% of the target, and the NEOWISE "
                      "centroid stayed on the star.", confidence=0.01)["hypothesis"]
for hid, why in ((a, "two independent instruments, same night"), (b, "no neighbour can supply the flux; centroid fixed")):
    tb.update_hypothesis(C, hid, "rejected", reason=why)
p = tb.register_prediction(
    C,
    "Gaia DR4 epoch photometry will show the star at least 1.0 mag brighter in G on its brightest night between 2017 Jul 20 and Sep 23 "
    "(Gaia transits on Jul 27, Aug 22 and Sep 18) than its 2014-2017 median. The microlensing models predict -0.40, -0.88 and -2.07 "
    "mag on those dates.",
    0.8, "GAIA:G", 57954.0, 58019.0, "<", -1.0, statistic="brightest", baseline_start=56800.0, baseline_end=57900.0,
    hypothesis=h, resolve_by="2027-06-30")
print(ids, h, e, a, b, p)
