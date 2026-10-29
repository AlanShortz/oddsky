# DX And: the orbital period in the catalogues looks wrong, and the star is in outburst now

Status: **side result of H-0007, not refereed.** DX And (Gaia DR3 1925123677737599360; RA 352.44447, Dec +43.75108) is a known
U Gem-type dwarf nova with a K-type donor (VSX: UGSS, P = 0.440502 d; Ritter & Kolb: P_orb = 0.440502 d, K0/5). H-0007 recovered it
blind, as a ×3.4 grey NEOWISE brightening on 2018 Dec 13-14.

## 1. The photometric period is 0.44097 d, not 0.440502 d

- **Computed (TESS):** sectors 16, 17 (2019), 57 (2022) and 84 (2024). Two independent reductions agree:
  - FFI cutouts with a 3×3-pixel aperture (`scripts/hunt_h0007_tess.py`): combined f = 4.535438 c/d, 2P = 0.440972 d.
  - The official SPOC 2-minute PDCSAP light curves (TIC 428055818): combined 2P = 0.4409722 d.
- **What separates the two periods.** In any one sector the periodogram peak is broad: at the catalogue frequency the power is still
  about 95% of the peak. What separates them is where the peak falls and whether the phase holds across years:
  - The four SPOC sector peaks fall at 4.5351-4.5359 c/d (spread ±0.0003). The catalogue period implies 4.5403 c/d, about 0.005 c/d
    away, or ~15 times that spread.
  - A sinusoid at 4.535438 c/d keeps one phase across 2019-2024 (250°, 249°, 241°, 246°). At the catalogue frequency the phase wanders
    (198°, 151°, 37°, 218°). The combined power at the catalogue period is 0.006 against 0.71 (FFI) and 0.11 against 0.47 (SPOC; `scripts/hunt_h0007_dxand_spoc.py`).
- **Computed (ATLAS, independent):** quiescent ATLAS 2015-2026 (c and o separately, outbursts removed) peaks at 2P = 0.440971 d (o)
  and 0.440973 d (c). Power at the catalogue period: 0.002-0.004. ZTF r recovers 0.22049 d as well.
- **Inferred:** the 0.2205-d signal is ellipsoidal modulation of the Roche-lobe-filling donor (two humps per orbit), so P_orb = 0.440972 d
  (10.583 h). The catalogue value differs by 0.0024 cycles/day, close to a one-year alias (0.0027 c/d). A cycle-count error in the
  1990s radial-velocity period is the obvious suspect. Published periods disagree with each other as well: Drew et al. (1993) give 0.44167 d (K2 = 107 km/s), while the
  catalogue's 0.440502 d is the Bruch et al. (1997) radial-velocity ephemeris (per a web search; the papers themselves were not read).
  0.440972 d lies between the two and is inconsistent with both: in TESS and ATLAS phase coherence, and in power. Dağ et al. (2026, MNRAS 548, stag514; arXiv:2603.03539) analysed TESS 2-minute data
  for 2,544 CVs. Their appendix, which lists the ~116 systems whose periods they discuss or correct, does not include DX And
  (TIC 428055818, checked 2026-10-29). Their full table of 910 periods is not online yet (VizieR pending), so whether they list a
  period for DX And is unknown.

## 2. Outburst history (ATLAS 2015-2026, nights > 2× quiescence)

2016 Sep 29 - Oct 13; 2017 Aug 17-31; 2018 Dec 6-19 (also NEOWISE Dec 13-14 and ZTF r = 12.33 on Dec 19); 2022 Sep 17 - Oct 1 (also
ZTF g/i and the TESS sector 57 decline); 2024 Jan 31 - Feb 2; 2025 Aug 20 - Sep 3. Roughly one outburst a year, up to ×21 in c.
Many fall in seasonal gaps.

## 3. In outburst now

**Observed (ATLAS o):** 14.40 on 2026 Oct 22, 14.36-14.44 on Oct 23, **13.90 on Oct 25, 13.39 on Oct 26** (the latest data). A new
outburst began around Oct 23-24 and was still rising by about 0.5 mag/day. Spectroscopy or time-resolved photometry during this outburst,
and radial velocities in quiescence afterwards, would settle the period.
