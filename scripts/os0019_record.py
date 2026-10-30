"""OS-0019 (H-0008's J183040.98-220950.3): claims, hypotheses, Gaia predictions and status. Cites K1-K2.
A candidate, not an event: the ATLAS referee (hunts/H-0008/reviews/claude-referee-atlas-2026-10-30.md) finds tE unconstrained
(77 to >700 d) and a point lens that fits only with 80-90% blend light Gaia does not see; a symmetric bump fits better."""

from oddsky.case.store import CaseStore
from oddsky.tools import Toolbox

C = "OS-0019"
tb = Toolbox(mode="open", author="claude-opus-5.5")
ids = {}


def claim(key, text, tag, calls=None):
    ids[key] = tb.add_claim(C, text, tag, calls or [])["claim"]


claim("nw", "In the NEOWISE visit of 2022 Sep 8 the star was 0.47 mag brighter in W1 and 0.46 in W2 than its median (W1 9.70): "
      "x1.54, equal in both bands. W1 is otherwise flat to 0.7% rms over 2014-2024. Found blind by the H-0008 all-sky search.",
      "observed")
claim("atlas", "ATLAS (task 5272651) shows one brightening in 2015-2026, peaking in 2022 Aug: 2022 Aug 10-25 is 0.53 mag brighter "
      "in o and 0.49 mag in c than in 2023 Nov - 2026 (79 and 70 sigma). It rises from April and is back near baseline by "
      "December 2022. No other 20-day bin is above x1.05 in o.", "observed", ["K1", "K2"])
claim("ztf", "ZTF g and r (field 283) show the same brightening at the same flux ratio, 1.55-1.6 at the peak; the ZTF "
      "difference-image centroid of ZTF22aalviwh (38 alerts) is 0.09\" from the Gaia star.", "observed")
claim("colour", "The flux ratio is the same from ZTF g to WISE W2 (1.53-1.6 near the peak), and the bands peak together (2022 Aug "
      "15-20 within a few days).", "computed", ["K1", "K2"])
claim("shape", "A point lens fits only if 80-90% of the light in every band from g to W2 comes from an unresolved blend; Gaia sees "
      "no companion (RUWE 0.97, no multiple peaks) and resolves neighbours that give 3% of the ATLAS flux. With the blend fixed "
      "to Gaia's value the lens fit is worse by delta chi2 27-78, and a free symmetric bump fits better than any lens by 16-48. "
      "Robust: peak 2022 Aug 15-20, peak flux ratio 1.55-1.6, effective timescale |u0| tE about 35 d. tE itself is unconstrained.",
      "computed")
claim("star", "Gaia DR3 4090003970570642816 (G 14.3): an M giant (J-K 1.28, W1-W2 -0.17 from CO absorption), no infrared excess, "
      "l = 10.9, b = -5.6, toward the bulge.", "observed")
claim("lpv", "ALeRCE labels ZTF22aalviwh LPV/YSO, but its classifier has no microlensing class. As a pulsation it fails: the only "
      "period in the ATLAS baseline is 1.1% at 323 d, W1 varies by 0.7% rms in ten years, and a pulsation would be 3-10 times "
      "larger in g than in W1, not equal.", "inferred")
claim("novel", "Not found (2026-10-30) in TNS, the Gaia Science Alerts (60\"), KMTNet or OGLE EWS (outside both footprints), the ZTF "
      "microlensing catalogues, SIMBAD, VSX, ADS full text or a web search. Not checked: MOA 2022, ASAS-SN.", "observed")
h = tb.add_hypothesis(C, "microlensing", "A lens magnified the M giant in 2022 August, with a blend or a more complex lens (binary "
                      "source or lens, extended source) shaping the broad wings.",
                      supports=[ids[k] for k in ("nw", "atlas", "ztf", "colour")], conflicts=[ids["shape"]],
                      would_falsify="A repeat; a resolved colour change; Gaia DR5 flat in 2022.", confidence=0.65)["hypothesis"]
tb.add_hypothesis(C, "pulsation", "Long-period or semiregular variability of the M giant.", conflicts=[ids["lpv"], ids["colour"]],
                  would_falsify="Already disfavoured: no periodicity, flat W1, equal amplitude from g to W2.", confidence=0.10)
# The referee's remaining 0.20 is "unexplained": no intrinsic class gives one achromatic, symmetric brightening (claim shape).

DR4 = ("2014-07-25", "2020-01-20")
tb.register_prediction(C, "Gaia DR4 epoch photometry shows no repeat: in 2014 Jul - 2020 Jan no night is more than 0.3 mag brighter in "
                       "G than the DR4 median.", 0.80, "GAIA:G", *DR4, ">", -0.3, statistic="brightest", baseline_start=DR4[0],
                       baseline_end=DR4[1], hypothesis=h, resolve_by="2027-12-31")
tb.register_prediction(C, "Gaia DR5 sees the 2022 brightening: the brightest night in 2022 Feb - 2023 May is more than 0.3 mag brighter "
                       "in G than the 2015-2021 median (about -0.5 expected at the 2022 Sep 7 transit). DR5 is expected about 2030.",
                       0.85, "GAIA:G", "2022-02-01", "2023-05-31", "<", -0.3, statistic="brightest", baseline_start="2015-01-01",
                       baseline_end="2021-12-31", hypothesis=h, resolve_by="2032-12-31")
s = CaseStore.find(C)
c = s.load()
c.status = "reproduced"
c.summary = ("An M giant toward the Galactic bulge brightened once, by about 60%, peaking in 2022 mid-August, equally from g to 4.6 "
             "microns, and was back to normal by December. NEOWISE, ATLAS and ZTF all see it. It looks like microlensing, but a "
             "simple point lens fits only with a blend Gaia does not see, so it stays a candidate. Found blind by the H-0008 all-sky "
             "NEOWISE search.")
s.save(c)
print(ids, h, c.status)
