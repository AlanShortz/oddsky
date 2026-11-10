"""Twice-seen: the sky has already run part of your artificial-star test.

An artificial-star test puts fake stars of known brightness into an image and asks how many come back, how much too
bright, and with what scatter. It needs the images, the photometry code and weeks of computing, and it is redone for
every field. But many fields were imaged twice, once shallow and once deep, or once from the ground and once from space,
or reduced once with apertures and once with PSF fitting. Where a much deeper or sharper catalogue covers the same sky,
its stars are real stars of known brightness sitting at real positions in real crowding, and the other catalogue either
found them or did not.

`quality(truth, test)` ties the two catalogues, keeps the truth stars inside the sky both cover, and tabulates for the
test catalogue, by magnitude and by local crowding: the fraction recovered, the median offset, the scatter and the rate of
gross errors. `limit(table)` reads off the magnitude where recovery falls to one half.

Known gaps in the tool itself (hunts/H-0020 referee): matching is by position only, with no magnitude tolerance, so in
dense fields a wrong neighbour can stand in for a lost star; there is no colour axis, so a catalogue that requires a
second filter loses red or blue stars in a way this table averages over; and detector gaps are removed by a heuristic.

What this is not. It measures the test catalogue relative to the truth catalogue, so it is only valid well above the
truth catalogue's own limit (`horizon`, by default one magnitude brighter than the peak of the truth luminosity function);
fainter than that the table is marked `valid = False`. It cannot see stars both catalogues miss. Two catalogues of equal
resolution overstate completeness, however deep the truth is, because the same blend hides a star from both (in
simulation by 2.5 points for bright stars and 6 to 8 points a magnitude above the limit). And the truth stars follow the real luminosity function and the real spatial distribution: that is the right
weighting for the stars that are there, and the wrong one for a population that is not (a real artificial-star test can
ask about any star anywhere). Nothing here calls the network.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull, Delaunay, cKDTree

MATCH_ARCSEC = 0.07


def plane(ra, dec, ra0: float, dec0: float) -> np.ndarray:
    """Tangent-plane offsets in arcsec about (ra0, dec0); small fields only."""
    return np.c_[(np.asarray(ra, float) - ra0) * np.cos(np.radians(dec0)) * 3600.0, (np.asarray(dec, float) - dec0) * 3600.0]


def tie(a_xy: np.ndarray, a_mag: np.ndarray, b_xy: np.ndarray, radius: float = MATCH_ARCSEC, search: float = 3.0,
        n_bright: int = 6000, order: int = 3) -> dict | None:
    """Affine fit, then a smooth polynomial of degree `order`, taking catalogue A's positions onto B's; then the matches
    within `radius` arcsec.

    A coarse shift is found first from the histogram of offsets between A's brightest stars and every B star within
    `search` arcsec, so a catalogue-wide offset of an arcsecond does not defeat the match (H-0019 lost a third of a
    sample to an uncorrected 0.47" offset). Returns None when the catalogues do not overlap or cannot be tied; otherwise
    `ia`, `ib` (matched indices), `a_on_b` (A's positions in B's frame), `rms` (arcsec), `n_chance` (matches after shifting
    A by 3 arcsec: the chance rate), `shift` and `matrix`.
    """
    if len(a_xy) < 30 or len(b_xy) < 30:
        return None
    tb = cKDTree(b_xy)
    bright = np.argsort(a_mag)[:n_bright]
    near = tb.query_ball_point(a_xy[bright], search)
    off = np.array([b_xy[j] - a_xy[i] for i, js in zip(bright, near, strict=True) for j in js])
    if len(off) < 50:
        return None
    h, xe, ye = np.histogram2d(off[:, 0], off[:, 1], bins=int(20 * search), range=[[-search, search], [-search, search]])
    ix, iy = np.unravel_index(h.argmax(), h.shape)
    t = np.array([(xe[ix] + xe[ix + 1]) / 2, (ye[iy] + ye[iy + 1]) / 2])
    m = np.eye(2)
    for rad in (0.3, 0.12, radius, radius):
        d, j = tb.query(a_xy @ m.T + t, distance_upper_bound=rad)
        ok = np.isfinite(d)
        if ok.sum() < 30:
            return None
        sol, *_ = np.linalg.lstsq(np.c_[a_xy[ok], np.ones(ok.sum())], b_xy[j[ok]], rcond=None)
        m, t = sol[:2].T, sol[2]
    a_on_b = a_xy @ m.T + t
    # what an affine fit leaves between two pointings at different roll angles is a smooth distortion of a few hundredths
    # of an arcsecond, enough to lose a fifth of the stars at a 0.07" radius: remove it with a cubic in position
    if order > 1:
        c0, sc = a_on_b.mean(0), max(float(np.ptp(a_on_b, axis=0).max()) / 2, 1.0)

        def terms(xy):
            u, v = (xy[:, 0] - c0[0]) / sc, (xy[:, 1] - c0[1]) / sc
            return np.stack([u ** i * v ** k for i in range(order + 1) for k in range(order + 1 - i)], axis=1)

        fitted = a_on_b
        for rad in (0.25, 0.15, 0.10):
            d, j = tb.query(fitted, distance_upper_bound=rad)
            ok = np.isfinite(d)
            if ok.sum() < 200:
                break
            coef, *_ = np.linalg.lstsq(terms(a_on_b[ok]), b_xy[j[ok]] - a_on_b[ok], rcond=None)
            fitted = a_on_b + terms(a_on_b) @ coef
        a_on_b = fitted
    d, j = tb.query(a_on_b, distance_upper_bound=radius)
    ok = np.isfinite(d)
    dc, _ = tb.query(a_on_b + [3.0, 0.0], distance_upper_bound=radius)
    return {"ia": np.where(ok)[0], "ib": j[ok], "a_on_b": a_on_b, "rms": float(np.sqrt(np.mean(d[ok] ** 2))),
            "n_chance": int(np.isfinite(dc).sum()), "shift": t, "matrix": m}


def inside(points: np.ndarray, cloud: np.ndarray, shrink: float = 0.97) -> np.ndarray:
    """Which `points` lie inside the convex hull of `cloud`, shrunk about its centre so that edges are left out."""
    c = cloud.mean(0)
    hull = cloud[ConvexHull(cloud).vertices]
    return Delaunay((hull - c) * shrink + c).find_simplex(points) >= 0


def covered(points: np.ndarray, cloud: np.ndarray, cell: float = 8.0, min_neighbours: int = 7) -> np.ndarray:
    """Which `points` lie in sky the `cloud` catalogue covers, judged by occupancy: the point's `cell`-arcsec square and at
    least `min_neighbours` of the eight around it hold a cloud star. For catalogues stitched from several images, whose
    coverage has holes and ragged edges that a convex hull papers over."""
    lo = np.minimum(points.min(0), cloud.min(0)) - cell
    ij = np.floor((cloud - lo) / cell).astype(int)
    shape = tuple(np.floor((np.maximum(points.max(0), cloud.max(0)) - lo) / cell).astype(int) + 3)
    occ = np.zeros(shape, bool)
    occ[ij[:, 0], ij[:, 1]] = True
    pad = np.pad(occ, 1)
    nb = sum(pad[1 + dx:pad.shape[0] - 1 + dx, 1 + dy:pad.shape[1] - 1 + dy] for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0))
    good = occ & (nb >= min_neighbours)
    pij = np.floor((points - lo) / cell).astype(int)
    return good[pij[:, 0], pij[:, 1]]


def crowding(xy: np.ndarray, mag: np.ndarray, radius: float = 0.5, fainter_by: float = 1.0) -> np.ndarray:
    """For each star, the number of other stars within `radius` arcsec that are no more than `fainter_by` mag fainter
    than it: the neighbours bright enough to disturb its photometry."""
    tree = cKDTree(xy)
    out = np.zeros(len(xy), int)
    for i, js in enumerate(tree.query_ball_point(xy, radius)):
        out[i] = int((mag[js] < mag[i] + fainter_by).sum()) - 1
    return out


def horizon(truth_mag: np.ndarray, margin: float = 1.0, step: float = 0.1, snr: np.ndarray | None = None, min_snr: float = 10.0) -> float:
    """The faintest magnitude at which the truth catalogue can be trusted as truth. With the truth's signal-to-noise:
    the faintest 0.25-mag bin whose median S/N is at least `min_snr`. Without it: `margin` mag brighter than the peak of
    its luminosity function, which is a guess (in a galaxy the peak can be the red clump, not the catalogue's limit)."""
    if snr is not None:
        b = np.floor(np.asarray(truth_mag) / 0.25) * 0.25
        med = pd.Series(np.asarray(snr)).groupby(b).median()
        good = med[med >= min_snr]
        if len(good):
            return float(good.index.max() + 0.25)
    h, e = np.histogram(truth_mag, bins=np.arange(np.nanmin(truth_mag), np.nanmax(truth_mag) + step, step))
    return float(e[np.argmax(h)] - margin)


def quality(truth: pd.DataFrame, test: pd.DataFrame, mag_step: float = 0.25, radius: float = MATCH_ARCSEC,
            crowd_radius: float = 0.5, zero_point: bool = True, gross: float = 0.3, footprint: str = "hull",
            cell: float = 8.0, mag_max: float | None = None, displaced_radius: float = 0.25, gaps: bool = True) -> dict:
    """The test catalogue measured against the truth catalogue. Both need columns `ra`, `dec`, `mag` (same band).

    Returns `table` (one row per magnitude bin and crowding class: n, completeness corrected for chance matches (the raw
    recovered fraction and the chance rate are kept beside it) and its binomial error, median offset
    test minus truth, robust scatter, fraction of gross errors beyond `gross` mag, `valid`), `stars` (the truth stars in the
    common sky with `found`, `displaced`, `dmag`, `crowd`), and the tie's numbers. `mag_max` grades only truth stars
    brighter than it while still counting fainter ones as neighbours (cutting the truth catalogue first undercounts
    crowding: hunts/H-0020, referee). An optional truth column `snr` sets the horizon. `footprint="hull"` takes the common sky as the two
    catalogues' convex hulls (one pointing each); `"cells"` takes it from where the test catalogue has stars, in squares of
    `cell` arcsec (a stitched or patchy test catalogue). Crowding classes: "all", "isolated" (no disturbing
    neighbour within `crowd_radius`), "crowded" (one or more).
    """
    ra0, dec0 = float(truth.ra.median()), float(truth.dec.median())
    t_xy, s_xy = plane(truth.ra, truth.dec, ra0, dec0), plane(test.ra, test.dec, ra0, dec0)
    # tie on truth stars the test catalogue could have seen: a truth catalogue three magnitudes deeper is so dense that
    # any position finds a faint star by chance
    comparable = np.zeros(len(truth), bool)
    comparable[np.argsort(truth.mag.values)[:3 * len(test)]] = True        # by rank: no zero point is known yet
    fit = tie(s_xy, test.mag.values, t_xy[comparable] if comparable.sum() >= 30 else t_xy, radius=radius)
    if fit is None:
        raise ValueError("the catalogues do not overlap or could not be tied")
    s_on_t = fit["a_on_b"]
    if len(fit["ia"]) < 3 * max(fit["n_chance"], 1):
        raise ValueError(f"only {len(fit['ia'])} matches against {fit['n_chance']} expected by chance: not the same sky, or mirrored")
    common = covered(t_xy, s_on_t, cell) if footprint == "cells" else inside(t_xy, s_on_t) & inside(t_xy, t_xy)
    tree = cKDTree(s_on_t)
    d, j = tree.query(t_xy, distance_upper_bound=radius)
    found = np.isfinite(d)
    d_any, _ = tree.query(t_xy)
    # a truth star with no test source at `radius` but one within `displaced_radius` was seen and moved (a blend's centroid),
    # not missed: counted apart
    displaced = ~found & (d_any <= displaced_radius)
    if gaps:
        # holes in the test catalogue's coverage (a detector gap is a 2.5" empty strip): truth stars much farther from any
        # test star than test stars are from each other are outside its sky. This cannot tell a gap from a region where the
        # test catalogue lost everything, so it can only raise completeness.
        dd, _ = tree.query(s_on_t, k=2)
        common &= d_any <= max(1.0, 6.0 * float(np.median(dd[:, 1])))
    # chance: a truth star moved 3 arcsec away still "finds" a test star this often (it grows with the test density)
    dc, _ = tree.query(t_xy + [3.0, 0.0], distance_upper_bound=radius)
    chance = np.isfinite(dc)
    dmag = np.full(len(truth), np.nan)
    dmag[found] = test.mag.values[j[found]] - truth.mag.values[found]
    crowd = crowding(t_xy, truth.mag.values, crowd_radius)
    stars = pd.DataFrame({"ra": truth.ra.values, "dec": truth.dec.values, "mag": truth.mag.values, "found": found, "dmag": dmag,
                          "crowd": crowd, "chance": chance, "displaced": displaced})[common].reset_index(drop=True)
    hz = horizon(truth.mag.values[common], snr=truth.snr.values[common] if "snr" in truth else None)
    if mag_max is not None:      # grade only these; fainter truth stars were still counted as neighbours above
        stars = stars[stars.mag < mag_max].reset_index(drop=True)
    zp = 0.0
    if zero_point:
        ref = stars[stars.found & (stars.crowd == 0) & (stars.mag < np.nanpercentile(stars.mag[stars.found], 25))]
        zp = float(ref.dmag.median()) if len(ref) >= 20 else 0.0
        stars["dmag"] -= zp
    lo = np.floor(stars.mag.min() / mag_step) * mag_step
    stars["bin"] = lo + (np.floor((stars.mag - lo) / mag_step) + 0.5) * mag_step
    rows = []
    for cls, sel in (("all", np.ones(len(stars), bool)), ("isolated", (stars.crowd == 0).values), ("crowded", (stars.crowd > 0).values)):
        for m, g in stars[sel].groupby("bin"):
            n, k = len(g), int(g.found.sum())
            if n < 20:
                continue
            p = float(g.chance.mean())                      # chance-match probability in this bin
            c = float(np.clip((k / n - p) / (1 - p), 0.0, 1.0)) if p < 0.9 else np.nan
            dm = g.dmag[g.found]
            rows.append({"crowding": cls, "mag": round(float(m), 3), "n": n, "completeness": c, "raw_recovered": k / n, "chance": p, "displaced": float(g.displaced.mean()), "e_completeness": float(np.sqrt(max(c * (1 - c), 1.0 / n) / n)),
                         "offset": float(dm.median()) if k >= 5 else np.nan,
                         "scatter": float(1.4826 * np.median(np.abs(dm - dm.median()))) if k >= 5 else np.nan,
                         "gross": float((dm.abs() > gross).mean()) if k >= 5 else np.nan, "valid": bool(m <= hz)})
    return {"table": pd.DataFrame(rows), "stars": stars, "horizon": hz, "zero_point": zp, "n_truth_common": int(len(stars)),
            "n_matched": int(stars.found.sum()), "tie_rms_arcsec": fit["rms"], "n_chance": fit["n_chance"]}


def limit(table: pd.DataFrame, level: float = 0.5, crowding_class: str = "all") -> dict:
    """The magnitude where completeness first falls through `level` (linear interpolation between bins), and whether that
    happens inside the valid range. `mag` is None when completeness never falls that far in the table."""
    t = table[table.crowding == crowding_class].sort_values("mag")
    m, c, v = t.mag.values, t.completeness.values, t.valid.values
    for i in range(1, len(t)):
        if c[i - 1] >= level > c[i]:
            x = m[i - 1] + (c[i - 1] - level) / (c[i - 1] - c[i]) * (m[i] - m[i - 1])
            return {"mag": float(x), "valid": bool(v[i])}
    return {"mag": None, "valid": False}
