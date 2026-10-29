"""OS-0017: one more analysis call, then claims, hypotheses and status (cites call ids K1-K10)."""

import json

from oddsky.case.store import CaseStore
from oddsky.tools import Toolbox

C = "OS-0017"
tb = Toolbox(mode="open", author="claude-opus-5.5")
k10 = tb.compare_windows(C, "ATLAS:ATLAS_c", 58958, 58965, 57300, 58800)
print(json.dumps(k10, default=str)[:400])
ids = {}


def claim(key, text, tag, calls=None):
    ids[key] = tb.add_claim(C, text, tag, calls or [])["claim"]


claim("nw", "In the NEOWISE visit of 2020 Apr 9-10 the star was 0.744 mag brighter in W1 (12.309 against 13.053) and 0.731 mag "
      "brighter in W2 (12.387 against 13.118): a factor of 1.98, equal in both bands. 2,021 stars within 20' in the same frames "
      "are unchanged (referee, hunts/H-0007/reviews/claude-referee-J193353-2026-10-29.md).", "observed", ["K1", "K2"])
claim("flat", "Apart from that visit NEOWISE W1 is flat over 20 visits (2014-2024), robust scatter 0.025 mag.", "computed", ["K3"])
claim("atlas", "ATLAS o contains exactly one excursion in 2015-2026: brighter by 0.82 mag on 2020 Mar 11, the first night of the "
      "season, then declining for 57 days above the 0.2-mag threshold. On 2020 Apr 9-10 ATLAS o is 0.70 mag above its 2015-2019 "
      "median (22 sigma), and ATLAS c on Apr 22 is brightened by a similar amount, so the change is achromatic.", "observed",
      ["K4", "K5", "K10"])
claim("ztf", "ZTF r and g in 2020 Jun 15 - Jul 25 are 0.11 and 0.10 mag brighter than in 2018-2019 (9-10 sigma). After correction "
      "with 12 colour-matched stars in the same exposures, the star is 0.17 mag bright on Jun 18 and 0.08-0.10 on Jul 14-21; "
      "it is the only one of 84 stars in its CCD quadrant to move.", "observed", ["K7", "K8"])
claim("nb", "No Gaia DR3 source within 9.7\"; the brightest within 30\" (G = 18.3 at 17.8\") supplies under 7% of the target's G flux.",
      "observed", ["K9"])
claim("fit", "A point-source point-lens fit to nightly ATLAS c+o (scripts/hunt_h0007_j193353_fit.py, outside the Oddsky tools), with no "
      "blending or parallax, gives t0 = 2020 Mar 17, tE = 63 d, u0 = 0.43, A_max = 2.5 (chi2/dof 352/190, residual rms 2%). Without "
      "fitting them, it predicts the NEOWISE visit at x1.94 (observed x1.98) and the ZTF tail at x1.12 and x1.06 (observed x1.17 and "
      "x1.09). ATLAS has no 2020 data before Mar 11 or between Mar 11 and Apr 8, so the peak date and height are poorly constrained.",
      "computed")
claim("colour", "The extra light has the giant's own colour from ZTF g to WISE W2. A flare, accretion outburst or nova would be bluer "
      "and would not decline smoothly over six months.", "inferred", ["K1", "K2", "K7", "K8"])
claim("novel", "Not found (2026-10-29) in VSX, the ASAS-SN, ZTF, ATLAS or Gaia DR3 variable catalogues, TNS (60\"), SIMBAD (CfA mirror), "
      "the Gaia Science Alerts, KMTNet 2020 or a web search. Gaia transited the star on 2020 Feb 28, Mar 12 and Apr 17 without an "
      "alert; those epochs will be in DR5.", "observed")
claim("star", "The source is a K giant (BP-RP 1.26; Teff ~4,900 K with map extinction), beyond ~6 kpc from its parallax, and with a "
      "proper motion of 12.5 mas/yr moving at v_t > 350 km/s: probably a halo giant about 2.7 kpc below the Galactic plane.",
      "inferred")
h = tb.add_hypothesis(C, "microlensing", "A foreground star passed within ~0.4 Einstein radii of the halo giant, magnifying it about "
                      "2.5 times around 2020 mid-March.", supports=[ids[k] for k in ("nw", "flat", "atlas", "ztf", "fit", "colour")],
                      would_falsify="A repeat brightening; Gaia DR5 epoch photometry flat on 2020 Feb 28 / Mar 12 / Apr 17, or BP and RP "
                      "changing by different amounts.", confidence=0.95)["hypothesis"]
tb.add_hypothesis(C, "eruptive", "An outburst of an unseen companion, or a flare.", conflicts=[ids["colour"], ids["fit"]],
                  would_falsify="A colour change during the event, or a repeat.", confidence=0.03)
a = tb.add_hypothesis(C, "artifact_instrumental", "A NEOWISE, ATLAS or ZTF artifact.", conflicts=[ids["nw"], ids["atlas"], ids["ztf"]],
                      would_falsify="Already falsified: three instruments see the same event.", confidence=0.01)["hypothesis"]
b = tb.add_hypothesis(C, "artifact_blend", "A neighbouring source brightened.", conflicts=[ids["nb"], ids["nw"]],
                      would_falsify="Already falsified: no source within 9.7\"; NEOWISE centroid fixed.", confidence=0.01)["hypothesis"]
tb.update_hypothesis(C, a, "rejected", reason="NEOWISE, ATLAS and ZTF see the same event")
tb.update_hypothesis(C, b, "rejected", reason="no neighbour can supply the flux; centroid fixed")
s = CaseStore.find(C)
c = s.load()
c.status = "reproduced"
c.summary = ("A K giant in the Galactic halo, beyond about 6 kpc (l = 18, b = -19), brightened once in 2020: x2.4 in ATLAS on Mar 11, "
             "x2.0 in both ATLAS and NEOWISE W1/W2 on Apr 9-10, fading smoothly through ZTF's June-July tail and back to normal by "
             "October. The extra light has the star's own colour from g to 4.6 microns. A point lens fits (t0 about 2020 Mar 17, tE "
             "about 63 d, A_max about 2.5; the peak itself is unobserved). Nothing similar in 2014-2026. Not in VSX, TNS, SIMBAD, the "
             "Gaia alerts or KMTNet. Gaia DR5 will hold three transits during the event.")
s.save(c)
print(ids, h, c.status)
