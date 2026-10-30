"""Gravitational microlensing light curves: a point source magnified by a point lens, with optional annual parallax.

Written after hunt H-0007, where two referees had to fit the events by hand. What they learned is built in:
  * fit flux ratios, not magnitudes, with an error floor per series from its own baseline scatter;
  * a static lens can leave a rise/decline asymmetry that biases t0, tE and u0, so the parallax model is fitted beside it;
  * when the peak falls in a data gap, covariance errors are far too small, so ranges come from chi-square profiles (each
    point a full refit), after rescaling chi-square to one per degree of freedom;
  * with parallax, both signs of u0 are tried (the ecliptic degeneracy).

Parallax follows Gould (2004): the Sun's position seen from Earth, projected north/east at the target, minus its position and
velocity at t0par; tau += piE_N dN + piE_E dE, beta += -piE_N dE + piE_E dN. A satellite in low Earth orbit (NEOWISE) shares
Earth's parallax to far better than this precision.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import least_squares


def magnification(u) -> np.ndarray:
    u = np.maximum(np.abs(np.asarray(u, float)), 1e-6)
    return (u**2 + 2) / (u * np.sqrt(u**2 + 4))


def sun_offsets(t, ra: float, dec: float, t0par: float) -> tuple[np.ndarray, np.ndarray]:
    """Projected Sun position (AU) north and east at (ra, dec), minus its position and velocity at t0par."""
    import astropy.units as u
    from astropy.coordinates import get_body_barycentric
    from astropy.time import Time

    t = np.asarray(t, float)
    a, d = np.radians(ra), np.radians(dec)
    east = np.array([-np.sin(a), np.cos(a), 0.0])
    north = np.array([-np.sin(d) * np.cos(a), -np.sin(d) * np.sin(a), np.cos(d)])

    def proj(tt):
        xyz = -get_body_barycentric("earth", Time(np.atleast_1d(tt), format="mjd")).xyz.to(u.au).value.T
        return xyz @ north, xyz @ east

    grid = np.linspace(min(t.min(), t0par) - 2, max(t.max(), t0par) + 2, 600)
    sn, se = proj(grid)
    n0, e0 = proj(np.array([t0par - 1, t0par, t0par + 1]))
    dn = np.interp(t, grid, sn) - n0[1] - (n0[2] - n0[0]) / 2 * (t - t0par)
    de = np.interp(t, grid, se) - e0[1] - (e0[2] - e0[0]) / 2 * (t - t0par)
    return dn, de


@dataclass
class Problem:
    """Flux ratios f (flux / baseline) with errors e at times t, one series label per point."""
    t: np.ndarray
    f: np.ndarray
    e: np.ndarray
    group: np.ndarray
    ra: float | None = None
    dec: float | None = None
    parallax: bool = False
    blend: bool = False
    t0par: float | None = None
    _dn: np.ndarray | None = field(default=None, repr=False)
    _de: np.ndarray | None = field(default=None, repr=False)

    def __post_init__(self):
        self.t, self.f, self.e = (np.asarray(x, float) for x in (self.t, self.f, self.e))
        self.group = np.asarray(self.group)
        self.names = sorted(set(self.group.tolist()))
        self.gi = np.array([self.names.index(g) for g in self.group])
        if self.t0par is None:
            self.t0par = float(round(self.t[np.argmax(self.f)]))
        if self.parallax:
            if self.ra is None or self.dec is None:
                raise ValueError("parallax needs the target's ra and dec")
            self._dn, self._de = sun_offsets(self.t, self.ra, self.dec, self.t0par)

    # parameter vector: t0, tE, u0, [piE_N, piE_E], [fs per series]
    @property
    def nlens(self) -> int:
        return 5 if self.parallax else 3

    def model(self, p) -> np.ndarray:
        t0, te, u0 = p[0], p[1], p[2]
        tau = (self.t - t0) / te
        beta = np.full_like(self.t, u0)
        if self.parallax:
            tau = tau + p[3] * self._dn + p[4] * self._de
            beta = beta + (-p[3] * self._de + p[4] * self._dn)
        a = magnification(np.hypot(tau, beta))
        if not self.blend:
            return a
        fs = np.asarray(p[self.nlens:])[self.gi]
        return fs * a + 1 - fs

    def bounds(self, t0c: float):
        lo = [t0c - 300, 1.0, -3.0 if self.parallax else 1e-4] + ([-5.0, -5.0] if self.parallax else [])
        hi = [t0c + 300, 2000.0, 3.0] + ([5.0, 5.0] if self.parallax else [])
        if self.blend:
            lo += [0.02] * len(self.names)
            hi += [1.5] * len(self.names)
        return np.array(lo), np.array(hi)

    def starts(self, t0c: float):
        amax = max(float(np.max(self.f)), 1.05)
        ug = float(np.clip(np.sqrt(2.0 / max(amax**2 - 1, 1e-6)), 0.05, 1.5))
        for te in (15.0, 40.0, 100.0, 250.0):
            for s in ((1, -1) if self.parallax else (1,)):
                for pi in (((0.0, 0.0), (0.3, 0.3), (-0.3, 0.3)) if self.parallax else ((),)):
                    yield [t0c, te, s * ug, *pi] + ([0.9] * len(self.names) if self.blend else [])

    def fit(self, fixed: dict[int, float] | None = None, t0c: float | None = None):
        """Best fit; `fixed` pins parameters by index (for profiles)."""
        fixed = fixed or {}
        t0c = float(self.t[np.argmax(self.f)]) if t0c is None else t0c
        lo, hi = self.bounds(t0c)
        free = [i for i in range(len(lo)) if i not in fixed]

        def full(q):
            p = np.empty(len(lo))
            p[free] = q
            for i, v in fixed.items():
                p[i] = v
            return p

        best = None
        for p0 in self.starts(t0c):
            q0 = np.clip(np.asarray(p0, float)[free], lo[free] + 1e-6, hi[free] - 1e-6)
            r = least_squares(lambda q: (self.model(full(q)) - self.f) / self.e, q0, bounds=(lo[free], hi[free]))
            if best is None or r.cost < best.cost:
                best = r
        return full(best.x), float(2 * best.cost)


def profile_range(prob: Problem, p_best, chi2_best: float, index: int, half_width: float, n: int = 9,
                  level: float = 4.0, iters: int = 6) -> tuple[float, float, bool]:
    """Range of parameter `index` where the rescaled chi-square stays within `level` of the minimum (95% for 4).
    A coarse scan brackets each edge, then bisection finds the crossing. Returns (low, high, open); `open` is True if the
    range reaches the edge of the scanned window (the data do not bound it)."""
    dof = max(len(prob.t) - len(p_best), 1)
    scale = max(1.0, chi2_best / dof)
    center = float(p_best[index])
    t0c = float(p_best[0])
    floor = 1.0 if index == 1 else -np.inf

    def dchi(v):
        return (prob.fit({index: v}, t0c=t0c)[1] - chi2_best) / scale

    def edge(sign):
        step = half_width / (n // 2)
        inside, v = center, center
        for _ in range(n // 2):
            v = max(inside + sign * step, floor)
            if v == inside or dchi(v) >= level:
                break
            inside = v
        else:
            return inside, True
        if v == inside:
            return inside, True
        outside = v
        for _ in range(iters):
            mid = (inside + outside) / 2
            if dchi(mid) < level:
                inside = mid
            else:
                outside = mid
        return (inside + outside) / 2, False

    lo, open_lo = edge(-1)
    hi, open_hi = edge(+1)
    return float(lo), float(hi), bool(open_lo or open_hi)


def coverage(t, t0: float, te: float, u0: float) -> dict:
    """How well the data sample the event: points in the peak (|t - t0| < max(|u0|, 0.1) tE) and on each wing (2 tE)."""
    t = np.sort(np.asarray(t, float))
    core = np.abs(t - t0) < max(abs(u0), 0.1) * te
    inside = t[np.abs(t - t0) < te]
    gaps = np.diff(np.r_[t0 - te, inside, t0 + te])
    return {"n_peak": int(core.sum()), "n_rise": int(((t < t0) & (t > t0 - 2 * te)).sum()),
            "n_decline": int(((t > t0) & (t < t0 + 2 * te)).sum()),
            "largest_gap_within_1tE_days": round(float(gaps.max()), 1)}
