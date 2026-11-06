# Prior-art note, 2026-11-06

From a separate agent told to look for reports that the sense of Gaia astrometric orbits depends on ecliptic hemisphere. It read
papers in full text (arXiv PDF) and searched them for clockwise, retrograde, prograde, direct, sense, handed, chiral, ecliptic,
cos i, degeneracy and one year. Its verdict: **partially known.** The mechanism is published; no report found of the signed-cos i /
ecliptic-hemisphere signal in Gaia or Hipparcos data, or of a half-year sign reversal.

- **Butkevich 2018, MNRAS 476, 5658** (arXiv:1709.00290), read through §4.5, rest searched. §3.1: "the host star and Earth revolve
  in the same direction, if iE < π/2". §4.3: "for iE > 90° the correlation decreases since the star and Earth revolve in opposite
  directions." Theory only: continuous sampling, parallax-only fit, no data test, no half-year term in its correlation.
- **Halbwachs+ 2023 (A&A 674 A9):** "lack of one-year periods, which comes from a degeneracy between parallactic and orbital motion" (§7). Nothing on sense.
- **Holl+ 2023 (A10):** one-year aliases only (§6.2.4).
- **Holl+ 2023 (A25):** a constant offset "traces out a circle" and fits P = 1 yr (§5.4.2). Nothing on sense.
- **Arenou+ 2023 (A34):** "difficulty to decouple the orbital from the parallactic effect". Signed cos i only all-sky (Fig. 11).
- **El-Badry+ 2024 (OJAp):** "orbital motion is degenerate with parallactic motion" (§4.5). Signed cos i all-sky (Fig. 5), no hemisphere split.
- **Lam+ 2025 (ApJ 987, 215):** degeneracy (§4.4.1). Samples |cos i|, so it cannot carry the sign.
- **Penoyre+ 2022:** "orientations aligned such that their motion mimics the parallax ellipse" (§4.3); cites Butkevich. No sense stated.
- **Babusiaux+ 2023:** nothing relevant.

Not read: Holl 2011 technical report, Perryman 2014, Exoplanet Handbook, Pourbaix 2000, and any Hipparcos paper. ADS and web searches
found nothing for Hipparcos, which is weaker than reading the papers. `gaiamock`'s code keeps signed inclinations and uses the real
along-scan parallax factor, so it should reproduce the effect if split by hemisphere (code read, not run).

My own ADS searches: the citation trees of Agati+ 2015, Glebocki 2000 and Butkevich 2018 (7 citing papers), and full-text queries on
orbital poles and wide-binary angular momentum. Closest on the Galactic question: Seto 2024 and Seto & Liu 2026 (LISA dipole, no
measurement), Makarov 2026 (projected momenta, assumes isotropy), Bozza & Rota 2025 (66 microlensing planets).
