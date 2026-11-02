"""v2 masks: which unWISE "bright star" footprints are really the galaxy, and where subtraction is
impossible.

The unWISE bitmask (Meisner et al. 2019, PASP 131, 124504, Table 2 and appendix A) draws its bright-star
footprints from a bright-source list: AllWISE w1mpro < 9.5 or w2mpro < 8.3, plus 2MASS Ks < 5. A
nearby galaxy's nucleus, bulge or starburst is in that list (AllWISE fits it as one or several "point
sources"), so bits 0-5 and the spike bits 27-30 paint a 1-2' star footprint over the galaxy's brightest
light. In run h0012a that blanked 92% of M82's W1 light, including SN 2014J (referee report
hunts/H-0012/reviews/claude-referee-triage-2026-11-01.md, section 3).

Bits used here:
  0-3   bright star core and wings (W1/W2 x two scan directions)     -> STAR_FOOT
  4, 5  bright star saturation (W1, W2), MODEL-predicted like 0-3   -> SATURATION
  7, 8  bright star centroid off the tile edge (W1, W2)                -> never released (star unseen)
  21,22 "may contain bright star centroid" (3x3 px at each source)    -> star centres (released with the footprint)
  27-30 PSF-based and geometric diffraction spikes                    -> STAR_SPIKE

v2 rule. Every bright-star footprint pixel (STAR_FOOT | STAR_SPIKE) is assigned to the bright source
whose footprint it most plausibly belongs to: the nearest star centre in units of the footprint size,
d / F^(1/3) (a PSF wing ~ r^-3 thresholded at a fixed level reaches r ~ F^(1/3)). Star centres are the
bit-21/22 markers plus the catalogue positions. A footprint pixel is RELEASED (searched) when its source
is galaxy light:
  - catalogue verdict (preferred; hunts/H-0012/scripts/targets.py writes it): the AllWISE bright source
    has no Gaia DR3 counterpart with a significant parallax or proper motion (> 5 sigma). Genuine
    foreground stars always do at W1 < 9.5;
  - fallback, without a catalogue: the source sits within the galaxy's nucleus radius of a galaxy core
    (its centre, or a companion / neighbouring target's centre), and the reference image there is
    extended (concentration below 0.8 x the PSF's).
A marker with no catalogue match is a star (kept), weighted by its reference-image flux (never below the
list's W1 = 9.5 limit). Bits 4/5 are the bitmask's MODEL of where the catalogued
source saturates; for galaxy light they are released with the footprint, and saturation is taken from the
data instead: pixels covered in fewer than half the epochs (unWISE drops saturated exposures; M82's core
has n = 0 in some epochs). Those, plus bits 4/5 of genuine stars, stay masked and are reported as
SATURATED, not dropped silently. Centroid-off-edge bits (7/8) are never released. Released pixels are LOW-CONFIDENCE: searched with a
16-px local noise calibration (pipeline.Config.fine_box) and flagged on every candidate that sits there.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage

from . import PIXSCALE

STAR_FOOT = (0, 1, 2, 3)
SATURATION = (4, 5)
OFF_EDGE = (7, 8)
CENTROID = (21, 22)
STAR_SPIKE = (27, 28, 29, 30)


def bits(*groups) -> int:
    return sum(1 << b for g in groups for b in g)


FAMILY_BITS = bits(STAR_FOOT, SATURATION, CENTROID, STAR_SPIKE)  # what may be released (a source's model footprint)
KEEP_BITS = bits(OFF_EDGE)  # never released

# maskbits.npy (uint8) codes, one bit per mask component
MB_INVALID, MB_STAR, MB_NUCLEUS, MB_OUTSIDE, MB_LOWCONF, MB_SATURATED, MB_HSB = (1, 2, 4, 8, 16, 32, 64)
MB_NAMES = {MB_INVALID: "invalid", MB_STAR: "star/artefact", MB_NUCLEUS: "nucleus/companion", MB_OUTSIDE: "outside",
            MB_LOWCONF: "low-confidence (released galaxy core)", MB_SATURATED: "saturated", MB_HSB: "high surface brightness"}


def describe(code: int) -> str:
    return ",".join(n for b, n in MB_NAMES.items() if int(code) & b) or "clear"


def concentration(img: np.ndarray, x: float, y: float, r1: float = 1.5, r2: float = 4.0, a0: float = 6.0,
                  a1: float = 9.0) -> float:
    """Background-subtracted flux within r1 over flux within r2 (px), background = median in the a0-a1
    annulus. A point source gives the PSF's value (~0.6-0.8 for unWISE); galaxy cores 0.25-0.5."""
    h = int(np.ceil(a1)) + 1
    xi, yi = int(round(x)), int(round(y))
    if xi - h < 0 or yi - h < 0 or xi + h >= img.shape[1] or yi + h >= img.shape[0]:
        return np.nan
    s = np.asarray(img[yi - h:yi + h + 1, xi - h:xi + h + 1], float)
    yy, xx = np.mgrid[-h:h + 1, -h:h + 1]
    rr = np.hypot(xx - (x - xi), yy - (y - yi))
    ann = (rr >= a0) & (rr < a1) & np.isfinite(s)
    if ann.sum() < 10:
        return np.nan
    s = s - np.median(s[ann])
    f2 = np.nansum(s[rr <= r2])
    return float(np.nansum(s[rr <= r1]) / f2) if f2 > 0 else np.nan


def psf_concentration(psf: np.ndarray) -> float:
    c = psf.shape[0] // 2
    pad = np.pad(psf, 12)
    return concentration(pad, c + 12, c + 12)


@dataclass
class StarCentre:
    x: float
    y: float
    flux: float  # relative W1 brightness (nmgy) used for the footprint weighting
    own: bool  # galaxy light (released) vs a genuine star (kept)
    why: str
    ra: float = np.nan
    dec: float = np.nan


@dataclass
class MaskSet:
    invalid: np.ndarray
    bright: np.ndarray  # masked: reference-peak circles + every unWISE artefact bit NOT released
    bright_all: np.ndarray  # the v1 mask (every ARTIFACT_BITS pixel): kernel fits and PSF stars avoid it
    nucleus: np.ndarray  # nucleus circle and companion circles
    outside: np.ndarray
    lowconf: np.ndarray  # released galaxy-core footprint: searched, flagged
    saturated: np.ndarray  # masked: subtraction impossible
    hsb: np.ndarray  # high surface brightness: 16-px noise calibration
    stars: list = field(default_factory=list)

    @property
    def noise_mask(self) -> np.ndarray:
        return self.invalid | self.bright | self.nucleus | self.saturated

    @property
    def det_mask(self) -> np.ndarray:
        return self.noise_mask | self.outside

    @property
    def fine(self) -> np.ndarray:
        return self.hsb | self.lowconf

    def codes(self) -> np.ndarray:
        out = np.zeros(self.invalid.shape, np.uint8)
        for m, b in ((self.invalid, MB_INVALID), (self.bright, MB_STAR), (self.nucleus, MB_NUCLEUS),
                     (self.outside, MB_OUTSIDE), (self.lowconf, MB_LOWCONF), (self.saturated, MB_SATURATED),
                     (self.hsb, MB_HSB)):
            out[m] |= b
        return out

    def census(self, ref: np.ndarray | None = None) -> dict:
        """Fractions of the search area (and of the sky-subtracted reference light in it) per component,
        v2 against the v1 rule (invalid | every artefact bit | nucleus)."""
        s = ~self.outside
        n = max(int(s.sum()), 1)
        v1 = self.invalid | self.bright_all | self.nucleus
        v2 = self.det_mask
        out = dict(search_px=int(s.sum()), masked_v1=float((v1 & s).sum() / n), masked_v2=float((v2 & s).sum() / n),
                   star_kept=float((self.bright & s).sum() / n), released_lowconf=float((self.lowconf & s & ~v2).sum() / n),
                   saturated=float((self.saturated & s).sum() / n), nucleus=float((self.nucleus & s).sum() / n),
                   invalid=float((self.invalid & s).sum() / n), hsb=float((self.hsb & s).sum() / n),
                   n_bright_sources=len(self.stars), n_released_sources=sum(st.own for st in self.stars),
                   released=[dict(ra=round(st.ra, 5), dec=round(st.dec, 5), why=st.why) for st in self.stars if st.own][:20],
                   kept_near=[dict(ra=round(st.ra, 5), dec=round(st.dec, 5), why=st.why) for st in self.stars
                              if not st.own and np.isfinite(st.ra)][:20])
        if ref is not None:
            sky = np.nanmedian(ref[self.outside & ~self.invalid]) if (self.outside & ~self.invalid).any() else 0.0
            light = np.clip(np.nan_to_num(np.asarray(ref, float) - sky), 0, None) * s
            tot = max(float(light.sum()), 1e-9)
            out.update(light_masked_v1=float((light * v1).sum() / tot), light_masked_v2=float((light * v2).sum() / tot),
                       light_lowconf=float((light * (self.lowconf & ~v2)).sum() / tot))
        return out


def star_centres(msk: np.ndarray) -> np.ndarray:
    """(N, 2) x, y of the bit-21/22 'may contain bright star centroid' markers (3x3 px blobs)."""
    m = (msk & bits(CENTROID)) != 0
    if not m.any():
        return np.zeros((0, 2))
    lab, n = ndimage.label(m, structure=np.ones((3, 3)))
    cy_cx = ndimage.center_of_mass(m, lab, range(1, n + 1))
    return np.array([(cx, cy) for cy, cx in cy_cx], float).reshape(-1, 2)


def classify_centres(msk: np.ndarray, wcs, gal, ref=None, psf=None, ref_off=(0, 0),
                     match_arcsec: float = 6.0) -> list[StarCentre]:
    """Star centres on the (padded) bitmask cut-out `msk`; `wcs` is the cut-out's WCS; `ref` is the
    reference image whose pixel (0, 0) is cut-out pixel ref_off (x, y). Each centre is own (galaxy light)
    or a star; see the module docstring."""
    cen = star_centres(msk)
    out: list[StarCentre] = []
    cat = list(getattr(gal, "bright_sources", ()) or ())
    used = set()
    if cat:
        cra = np.array([c[0] for c in cat], float)
        cdec = np.array([c[1] for c in cat], float)
        cx, cy = wcs.all_world2pix(cra, cdec, 0)
        inside = (cx > -50) & (cx < msk.shape[1] + 50) & (cy > -50) & (cy < msk.shape[0] + 50)
        for k in np.nonzero(inside)[0]:
            ra, dec, w1, is_star = cat[k][:4]
            f = 10 ** ((22.5 - (w1 if np.isfinite(w1) else 9.5)) / 2.5)
            out.append(StarCentre(float(cx[k]), float(cy[k]), f, not bool(is_star),
                                  "catalogue: Gaia star" if is_star else "catalogue: no Gaia star (galaxy light)", ra, dec))
            used.add(len(out) - 1)
    tol = match_arcsec / PIXSCALE
    for x, y in cen:
        if out:
            d = np.hypot(np.array([s.x for s in out]) - x, np.array([s.y for s in out]) - y)
            if d.min() <= tol:
                continue  # the catalogue entry already represents it
        ra, dec = wcs.all_pix2world([[x, y]], 0)[0]
        own, why = False, "marker, no catalogue entry: star"
        if not cat:  # fallback rule
            cores = [(gal.ra, gal.dec)] + [tuple(c[:2]) for c in getattr(gal, "cores", ())] + [tuple(m[:2]) for m in gal.extra_masks]
            rad = max(gal.nucleus_mask_arcsec, 15.0)
            near = any(_sep(ra, dec, a, d) <= rad for a, d in cores)
            if near:
                c = np.nan
                if ref is not None:
                    c = concentration(ref, x - ref_off[0], y - ref_off[1])
                pc = psf_concentration(psf) if psf is not None else 0.62
                if np.isfinite(c) and c < 0.8 * pc:
                    own, why = True, f"fallback: at a galaxy core, extended (conc {c:.2f} < 0.8 x {pc:.2f})"
                else:
                    why = f"fallback: at a galaxy core but point-like or unmeasurable (conc {c:.2f}): kept"
        out.append(StarCentre(float(x), float(y), marker_flux(ref, x - ref_off[0], y - ref_off[1]), own, why, float(ra), float(dec)))
    return out


F_LIST = 10 ** ((22.5 - 9.5) / 2.5)  # the bright-source list's W1 limit (Meisner et al. 2019 A1), nmgy


def marker_flux(ref, x: float, y: float, r: float = 4.0) -> float:
    """Brightness of a bitmask star marker with no catalogue entry: background-subtracted reference flux
    within r px (an underestimate for saturated cores), never below the bright-list limit W1 = 9.5."""
    if ref is None:
        return F_LIST
    h = int(r) + 6
    xi, yi = int(round(x)), int(round(y))
    if xi - h < 0 or yi - h < 0 or xi + h >= ref.shape[1] or yi + h >= ref.shape[0]:
        return F_LIST
    s = np.asarray(ref[yi - h:yi + h + 1, xi - h:xi + h + 1], float)
    yy, xx = np.mgrid[-h:h + 1, -h:h + 1]
    rr = np.hypot(xx, yy)
    ann = (rr > r + 2) & np.isfinite(s)
    if ann.sum() < 10:
        return F_LIST
    f = np.nansum(s[rr <= r] - np.median(s[ann]))
    return float(max(f, F_LIST)) if np.isfinite(f) else F_LIST


def _sep(ra1, dec1, ra2, dec2) -> float:
    dra = ((ra1 - ra2 + 180) % 360 - 180) * np.cos(np.radians((dec1 + dec2) / 2))
    return float(np.hypot(dra, dec1 - dec2) * 3600)


def release_map(msk: np.ndarray, centres: list[StarCentre]) -> np.ndarray:
    """Boolean map of FAMILY_BITS pixels whose footprint source is galaxy light (multiplicatively
    weighted Voronoi: nearest centre in d / F^(1/3))."""
    fam = (msk & FAMILY_BITS) != 0
    rel = np.zeros(msk.shape, bool)
    if not fam.any() or not any(c.own for c in centres):
        return rel
    ys, xs = np.nonzero(fam)
    best = np.full(ys.size, np.inf)
    owner = np.full(ys.size, -1)
    for k, c in enumerate(centres):
        d = np.hypot(xs - c.x, ys - c.y) / np.cbrt(max(c.flux, 1.0))
        better = d < best
        best[better], owner[better] = d[better], k
    own = np.array([c.own for c in centres])
    ok = (owner >= 0) & own[np.clip(owner, 0, None)]
    rel[ys[ok], xs[ok]] = True
    return rel & ((msk & KEEP_BITS) == 0)
