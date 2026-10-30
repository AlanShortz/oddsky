"""OS-0018 (H-0008's J180624.78-090411.4): claims, hypotheses, Gaia predictions and status. Cites lens_fit call K1.
The prediction wording follows the ATLAS referee (hunts/H-0008/reviews/claude-referee-atlas-2026-10-30.md, section 4): Gaia's
scanning law (GOST) puts only 2 transits in a Sep-Oct 2022 window, so the DR5 check spans 2022 Feb - 2023 May."""

from oddsky.case.store import CaseStore
from oddsky.tools import Toolbox

C = "OS-0018"
tb = Toolbox(mode="open", author="claude-opus-5.5")
ids = {}


def claim(key, text, tag, calls=None):
    ids[key] = tb.add_claim(C, text, tag, calls or [])["claim"]


claim("nw", "In the NEOWISE visit of 2022 Aug 31 the star was 1.37 mag brighter in W1 and 1.38 mag brighter in W2 than its 20-visit "
      "median (W1 11.53, robust scatter 0.02 mag): a factor of 3.5, equal in both bands. No other visit in 2014-2024 departs from the "
      "median by more than 0.15 mag. Found blind by the H-0008 all-sky search.", "observed")
claim("atlas", "ATLAS (task 5272650, four units, c and o) shows one event in 2015-2026: the star rises from x1.1 in March 2022 to "
      "x4.9 (o) and x5.0 (c) on 2022 Sep 18-20, falls to x2.1 by late November and x1.2 by February 2023. The peak is sampled on "
      "24-26 nights. No other 20-day bin in 2015-2026 is above x1.10.", "observed", ["K1"])
claim("ztf", "ZTF r (field 1428, catflags 0) catches the rise in 2022 at the same flux ratio as ATLAS o.", "observed")
claim("fit", "A point-lens fit to ATLAS o and c (lens_fit, baseline 2023 Nov - 2026) gives t0 = 2022 Sep 19 (MJD 59840.7-59842.1), "
      "tE 108-139 d (95%), A_max 4.5-5.5, fs 0.87-1.1, chi2 252 for 291 dof. Across 18 reduction choices with ATLAS, ZTF and "
      "NEOWISE together (referee), t0 is Sep 19-20 and tE 113-153 d; quote tE = 115-150 d. Separate rise and decline timescales "
      "agree (ratio 0.91-0.95).", "computed", ["K1"])
claim("shape", "The point lens beats a free symmetric bump with lens-like wings (Pearson VII, same per-series freedom) by "
      "delta chi2 = 26-88 depending on the reduction, and a fast-rise exponential-decay pulse by about 4,000.", "computed")
claim("colour", "The source flux changes by the same factor from ATLAS c to WISE W2: fitted alone, c and o peak within 0.3 d of each "
      "other with the same timescale. Blend fractions fall from 0.84-0.98 (c) to 0.68-0.73 (W1/W2), as expected from the red "
      "neighbours Gaia resolves (G 18.1 at 6.1\", G 20.2 at 2.5\") inside WISE's 6\" beam.", "computed")
claim("drift", "Before 2019 ATLAS reads the star 10-40% faint, stepping up when each unit's PSF narrows (02a between 2017 and 2018, "
      "01a between 2019 and 2020): flux against PSF width is -0.13 mag/px in o. NEOWISE W1 is flat to 0.001 +- 0.009 mag over the "
      "same years. The drift is instrumental and does not change the fit.", "computed")
claim("star", "Gaia DR3 4158424169627436800: a reddened K giant or subgiant (GSP-Phot Teff 4770 K, A_G 3.6), parallax -0.32 +- 0.13 "
      "mas (beyond ~5 kpc), no infrared excess (W1-W2 -0.13, W2-W3 0.10), l = 19.7, b = +5.7.", "observed")
claim("par", "Annual parallax improves the fit by delta chi2 4-36 depending on the reduction, along one direction (piE_N about -0.2). "
      "That is a hint, not a measurement. Without the angular Einstein radius no lens mass is measured: allowed masses run from "
      "about 0.3 to 10 solar masses.", "inferred", ["K1"])
claim("novel", "Not found (2026-10-30) in TNS (valid empty result), the Gaia Science Alerts (60\"), the KMTNet and OGLE EWS lists "
      "(outside both footprints), the ZTF microlensing catalogues (Zhai+2024, Rodriguez+2022, Medford+2023), ALeRCE/Lasair, SIMBAD, "
      "VSX, ADS full text or a web search. ZTF22abjkknd, the ZTF object at this position, has only 2025-26 negative-difference "
      "alerts. Not checked: MOA 2022 (page empty), ASAS-SN (server errors).", "observed")
h = tb.add_hypothesis(C, "microlensing", "A foreground star or remnant passed within ~0.2 Einstein radii of the giant, magnifying it "
                      "about 5.4 times on 2022 Sep 19, with tE about 115-150 d.",
                      supports=[ids[k] for k in ("nw", "atlas", "ztf", "fit", "shape", "colour")],
                      would_falsify="A repeat brightening; Gaia DR5 epoch photometry flat during 2022; BP and RP changing by "
                      "different amounts.", confidence=0.95)["hypothesis"]
tb.add_hypothesis(C, "eruptive", "An outburst of the star or an unseen companion (Be/shell, YSO accretion, nova, symbiotic).",
                  conflicts=[ids["shape"], ids["colour"], ids["star"]],
                  would_falsify="Already strongly disfavoured: symmetric lens shape, no colour change, no infrared excess, no "
                  "repeat in 11 years.", confidence=0.03)
a = tb.add_hypothesis(C, "artifact_instrumental", "An artifact in one survey.", conflicts=[ids["nw"], ids["atlas"], ids["ztf"]],
                      would_falsify="Already falsified: NEOWISE, ATLAS (four units) and ZTF see the same event.",
                      confidence=0.01)["hypothesis"]
tb.update_hypothesis(C, a, "rejected", reason="NEOWISE, ATLAS and ZTF see the same event")

DR4 = ("2014-07-25", "2020-01-20")
tb.register_prediction(C, "Gaia DR4 epoch photometry shows no repeat: in 2014 Jul - 2020 Jan no night is more than 0.5 mag brighter in "
                       "G than the DR4 median (a lens does not repeat; a Be star, YSO or nova usually would).", 0.85, "GAIA:G",
                       *DR4, ">", -0.5, statistic="brightest", baseline_start=DR4[0], baseline_end=DR4[1], hypothesis=h,
                       resolve_by="2027-12-31")
tb.register_prediction(C, "ATLAS's low 2015-16 flux is instrumental: Gaia DR4's median G in 2014 Jul - 2016 Jun is less than 0.1 mag "
                       "fainter than in 2018 Jan - 2020 Jan.", 0.90, "GAIA:G", "2014-07-25", "2016-06-30", "<", 0.1,
                       baseline_start="2018-01-01", baseline_end="2020-01-20", resolve_by="2027-12-31")
tb.register_prediction(C, "... and less than 0.1 mag brighter (the two-sided form of the same test).", 0.95, "GAIA:G", "2014-07-25",
                       "2016-06-30", ">", -0.1, baseline_start="2018-01-01", baseline_end="2020-01-20", resolve_by="2027-12-31")
tb.register_prediction(C, "Gaia DR5 epoch photometry sees the event: the brightest night in 2022 Feb - 2023 May is more than 1.2 mag "
                       "brighter in G than the 2015-2021 median. The lens model gives about -1.7 to -1.85 mag at the 2022 Sep 8 "
                       "transit. (DR5 is expected about 2030; the grader will need its release name.)", 0.85, "GAIA:G",
                       "2022-02-01", "2023-05-31", "<", -1.2, statistic="brightest", baseline_start="2015-01-01",
                       baseline_end="2021-12-31", hypothesis=h, resolve_by="2032-12-31")
tb.register_prediction(C, "Gaia DR5 sees the rising wing: median G in 2022 Feb-Apr is more than 0.1 mag brighter than in 2015-2021.",
                       0.80, "GAIA:G", "2022-02-01", "2022-04-30", "<", -0.1, baseline_start="2015-01-01",
                       baseline_end="2021-12-31", hypothesis=h, resolve_by="2032-12-31")
tb.register_prediction(C, "Gaia DR5 sees the falling wing: median G in 2023 Mar-Apr is more than 0.1 mag brighter than in 2015-2021.",
                       0.85, "GAIA:G", "2023-03-01", "2023-04-30", "<", -0.1, baseline_start="2015-01-01",
                       baseline_end="2021-12-31", hypothesis=h, resolve_by="2032-12-31")
s = CaseStore.find(C)
c = s.load()
c.status = "reproduced"
c.summary = ("A reddened giant 20 degrees from the Galactic centre and 6 degrees off the plane brightened once in 2022: x3.5 in "
             "NEOWISE on Aug 31, then x5 in ATLAS at the peak on Sep 19, back to normal by spring 2023. The rise and fall are "
             "symmetric and the same from 0.5 to 4.6 microns, and a point lens fits (tE about 115-150 d) better than any flexible "
             "bump. Found blind by the H-0008 all-sky NEOWISE search; not in any alert stream, catalogue or paper we could search.")
s.save(c)
print(ids, h, c.status)
