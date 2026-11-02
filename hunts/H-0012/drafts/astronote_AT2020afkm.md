# SUBMITTED 2026-11-02 as AstroNote 2026-308 (https://www.wis-tns.org/astronotes/astronote/2026-308). TNS AstroNote for AT 2020afkm (Oddsky OS-0030)

For Alan's review (Google Doc in alan@oddsky.ai Drive: https://docs.google.com/document/d/1XIkgh3isPNIAcfR0dvfahJTZuwXNymF1VYoAlImeieg/edit). Every number is from `reviews/ngc3239-check-2026-11-01.md` and the TNS pre-filing check
(`drafts/tns_OS-0030_validation.md`, which corrected the epoch times). Submit via https://www.wis-tns.org/astronotes →
"Add new AstroNote" (logged in), with AT 2020afkm as the related object and the figures listed at the end.

---

**Title:** AT 2020afkm: a dust-obscured infrared transient in NGC 3239 found in archival WISE data, with a fading Hubble
counterpart and a JWST dust remnant

**Authors:** A. Shortz (Oddsky)

**Related object:** AT 2020afkm

**Text:**

We report the discovery of AT 2020afkm, a mid-infrared transient in the irregular galaxy NGC 3239 (Arp 263; z = 0.00237,
distance about 7-12 Mpc), found in a blind difference-imaging search of 318 star-forming galaxies within 10 Mpc. The
search used the unWISE time-resolved coadds (NEO11 version, courtesy A. Meisner; Meisner, Lang & Schlegel 2018), 25
epochs from 2010 to 2024. As an acceptance test, the same search recovers the failed-supernova candidates M31-2014-DS1
(De et al. 2024) and N6946-BH1 blind. No optical transient was reported at this position.

**WISE.** Nothing is seen at the position in the 15 epochs from 2010 to 2020-04-28 (last non-detection 2020-04-28: W1 > 19.9 AB,
5 sigma). On 2020-11-23
the source is detected at W1 = 17.99 +- 0.04 and W2 = 17.67 +- 0.07 AB (difference fluxes 232 +- 8 and 310 +- 20 uJy;
28 and 15 sigma), and then fades: W1 = 18.96 and W2 = 18.63 AB on 2021-04-30, W1 = 19.92 AB on 2021-11-22, near the
detection limit by 2022. The field was in solar conjunction for much of the gap, so the rise (< 209 days) and the true
peak are not constrained; the first detection is a lower limit on the peak. The colour W1 - W2 = 0.95 +- 0.08 (Vega) at
the first two epochs corresponds to a blackbody of about 960 K, i.e. warm dust. The blackbody luminosity at the first
detection is about 5.6e5 L_sun at 7.9 Mpc (about twice that at 11 Mpc), and at least 3e46 erg was radiated in the
infrared afterwards. The W1 decline e-folds in about 170 days and slows later.

**Hubble.** Public WFC3/UVIS images taken on 2021-02-16 (programme 16179, PI Filippenko; 85 days after the first WISE
detection) show a point source at RA, Dec = 10:25:09.894, +17:09:49.60 (+- 0.004" statistical, Gaia-tied), 0.37" from
the WISE centroid (+- 0.2-0.3"). In difference images it has F606W = 25.93 +- 0.06 and F814W = 24.95 +- 0.06 AB (M_F814W
about -4.5 at 7.9 Mpc) and is detected in each of the four exposures. It is absent from ACS F606W images of 2022-12-11
(programme 15446, PI Dalcanton; > 27.1 AB) and from WFC3 images of 2025-01-09 (programme 17502, PI Thilker; F555W >
26.6 AB), with no residual star or cluster (M_V > -2.9). The chance that an unrelated source that vanishes like this
lies within 0.37" is about 0.2%.

**JWST.** Public NIRCam images from 2024-04-24 and 2024-05-22 (programme 3707, PI Leroy) show an unresolved source 0.01"
from the Hubble position at F300M = 22.65/22.50 and F335M = 21.97 AB, with nothing in F150W (> 26.5 AB). A blackbody fit
gives about 580 K and 3.6e4 L_sun: a cooler, fainter dust source that was not there before the event. Spitzer/IRAC in
2008 shows nothing at the position (nu L_nu(4.5 um) < 4e3 L_sun, 3 sigma), which also excludes an infrared-bright
progenitor like that of SN 2008S.

**Other limits.** ATLAS has no detection (3 sigma limits o > 20.4-21.7 in 2020 Oct to 2021 Jan); VLASS gives < 0.36 mJy
at 3 GHz on 2021-11-20; Chandra (2025) gives L_X < 3e37 erg/s. The source is 70.6" (about 2.7 kpc) from the centre of a
galaxy with no active nucleus.

**Interpretation.** The event is brighter in the infrared than the SPIRITS "SPRITEs" (M_[4.5] -11 to -14; Kasliwal et
al. 2017), but a normal core-collapse supernova fully hidden by dust does not fit well: the Hubble colour (V - I about
1.5) allows only A_V of about 1-2, while the faintness relative to the infrared would need A_V of about 9-20, and a fully
enshrouded Type II supernova should re-radiate 30-100 times more infrared light at this phase. A dust-obscured luminous
red nova (stellar merger), an ILRT-like eruption without a bright progenitor, or a low-energy supernova behind clumpy
dust all remain possible. The JWST remnant (F335M = 22.0 AB) is bright enough for NIRSpec and MIRI spectroscopy, which
could distinguish these: molecular bands such as CO and H2O would point to a merger, and [Ni II]/[Fe II] lines or
silicate dust to a supernova. We encourage such follow-up.

Oddsky (oddsky.ai) is an open project that searches public sky-survey archives for unreported astronomical events; the
full analysis, data and code for this object are public as Oddsky case OS-0030.

**Acknowledgements:** unWISE time-resolved coadds (NEO11 version, courtesy A. Meisner; Meisner, Lang & Schlegel 2018).
This work uses data from WISE/NEOWISE (NASA/JPL/IPAC, via IRSA), from the NASA/ESA Hubble and NASA/ESA/CSA James Webb
Space Telescopes obtained from MAST (programmes HST 16179, 15446, 17502 and JWST 3707), from Spitzer (IRSA), ATLAS,
VLASS (NRAO, via CADC) and Chandra.

**Figures (attach):**
1. `reviews/ngc3239-check-2026-11-01/summary.png` — overview (already attached to the AT report).
2. `reviews/ngc3239-check-2026-11-01/wise_lc.png` — WISE W1/W2 difference light curve 2010-2024.
3. `reviews/ngc3239-check-2026-11-01/hst_stamps.png` — HST 2021/2022/2025 at the position.
4. `reviews/ngc3239-check-2026-11-01/jwst_stamps.png` — JWST NIRCam F150W/F300M/F335M.

---

## Notes for Alan before submitting

- **Length:** about 900 words. That is normal for an AstroNote; it can be cut to the WISE and Hubble paragraphs plus the
  interpretation if you prefer a shorter note.
- **Authors:** "A. Shortz (Oddsky)". Add co-authors only with their agreement. Aaron asked for an acknowledgement, which is
  included, not authorship.
- **The TNS remarks give "70.6\" E" of the centre and the Hubble offset as 0.36"**; this note uses 0.37" from the
  fuller check. Both are within the errors.
