"""Astrometric + photometric microlensing with Gaia's one-dimensional (along-scan) epoch astrometry.

Photometry gives the Einstein time tE and, with annual parallax, the microlensing parallax piE; it does not give the lens
mass. The source's light centroid is deflected by the lens (amplitude ~ theta_E u/(u^2+2) for a dark lens), so astrometry
measures theta_E, and M = theta_E / (kappa piE), kappa = 4G/(c^2 au) = 8.144 mas/Msun.

Conventions (shared with `oddsky.analysis.lensing`, Gould 2004):
  * the trajectory is the lens-minus-source separation in units of theta_E, u = tau e_mu + beta e_perp, with
    tau = (t - t0)/tE + piE . s and beta = u0 + piE x s, where s = (dN, dE) is the projected Sun position seen from Earth,
    minus its position and velocity at t0par (`lensing.sun_offsets`). e_mu = (piE_N, piE_E)/|piE| is the direction of the
    lens-source relative proper motion; e_perp = (piE_E, -piE_N)/|piE| in (N, E) components;
  * the source images' light centroid moves away from the lens. With source flux 1, unrelated blend flux b at the source's
    position (fs = 1/(1+b) in the astrometric window) and lens flux g (a dark lens has g = 0), the shift relative to the
    unlensed light centroid is
        delta = theta_E u_SL { [A (u^2+3)/(u^2+2) + b] / (A + g + b) - (1 + b)/(1 + g + b) },   u_SL = -u,
    which reduces to theta_E u_SL/(u^2+2) * A fs/(A fs + 1 - fs) for g = 0 (Dominik & Sahu 2000, eqs. 93-99, plus third
    light). Maximum theta_E/sqrt(8) at u = sqrt(2) for g = 0, b = 0;
  * a blend that is NOT at the source's position (a neighbour inside Gaia's window) pulls the centroid toward the source as
    the source brightens: delta_b = -b_vec (1 - fs) [1/(A fs + 1 - fs) - 1]. Its direction b_vec is unknown, so it enters
    as two free linear terms in both the deflection and the no-deflection model (`blend_offset=True`): a detection must
    beat what an offset blend can do. Its time profile (proportional to A - 1, falling as u^-4) differs from the
    deflection's (falling as u^-1), which is what separates them;
  * Gaia's measurement is the along-scan abscissa w = dE sin(theta) + dN cos(theta) (+ parallax factor * parallax), with
    theta the scan position angle from north through east (Gaia DR4 `scan_pos_angle`; sin and cos are dw/dalpha* and
    dw/ddelta), times in MJD, the reference epoch J2017.5 (DR4's) unless set.

Model parameters: nonlinear q = (t0, tE, u0, piE_N, piE_E); everything else is linear given q and is solved exactly at each
step (variable projection): per photometric series the source fraction fs; astrometry: position offsets, proper motion,
parallax, theta_E (>= 0) and the two blend-offset terms. The astrometric blend fraction is the fs of the photometric series
named `fs_ast_group` (Gaia G by default: the same windows), capped at 1, or `fs_ast` if given.

Tests: tests/test_astrolens.py. Acceptance test and calibration: hunts/H-0015.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import least_squares
from scipy.stats import chi2 as chi2_dist

from .lensing import magnification, sun_offsets

KAPPA = 8.144              # mas / Msun
J2017_5 = 57936.375        # MJD of J2017.5, Gaia DR4's reference epoch
YEAR = 365.25
DR4_START, DR4_END = 56863.44, 58868.92   # 2014-07-25 10:30 .. 2020-01-20 22:00 UTC

# Along-scan scatter per CCD vs G: the robust scatter of AGIS post-fit residuals in Gaia EDR3 (Lindegren et al. 2021,
# A&A 649, A2, Fig. A.1, blue curve; digitised in astromet, Penoyre et al., data/scatteral_edr3.csv).
_G_CCD = np.array([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0])
_S_CCD = np.array([0.16, 0.15, 0.146, 0.143, 0.172, 0.248, 0.394, 0.660, 1.186, 2.317, 4.781, 10.0])
# Pre-launch end-of-mission centroiding errors with a 50% margin, per FoV transit (Rybicki et al. 2018, MNRAS 476, 2013,
# table 3; G 13.3-18.3), extended by a constant below 13.3 and photon scaling above 18.3: a pessimistic alternative.
_G_RYB = np.array([10.0, 13.3, 14.3, 15.3, 16.3, 17.3, 18.3, 19.3, 20.3, 21.3])
_S_RYB = np.array([0.056, 0.056, 0.089, 0.145, 0.244, 0.430, 0.818, 1.64, 3.3, 6.6])


def sigma_al_fov(g, model: str = "edr3", n_ccd: int = 8, floor: float = 0.05) -> np.ndarray:
    """Along-scan uncertainty (mas) of one field-of-view transit at magnitude G.

    "edr3": the EDR3 per-CCD residual scatter / sqrt(n_ccd) (8 AF CCDs used on average), plus a per-transit floor (attitude,
    calibration) in quadrature. "rybicki18": pre-launch per-FoV errors with a 50% margin (about 2x worse at G 15-18)."""
    g = np.asarray(g, float)
    if model == "edr3":
        s = np.exp(np.interp(g, _G_CCD, np.log(_S_CCD))) / np.sqrt(n_ccd)
        return np.hypot(s, floor)
    if model == "rybicki18":
        return np.exp(np.interp(g, _G_RYB, np.log(_S_RYB)))
    raise ValueError(f"unknown precision model {model!r}")


def sigma_g_transit(g) -> np.ndarray:
    """Per-transit Gaia G photometric uncertainty (mag), a smooth fit to DR3 epoch-photometry scatter in crowded fields:
    a 3 mmag floor, a background term and a source photon term."""
    g = np.asarray(g, float)
    x = g - 15.0
    return np.sqrt(0.003**2 + (0.0025 * 10 ** (0.2 * x)) ** 2 + (0.0006 * 10 ** (0.4 * x)) ** 2)


# ---------------------------------------------------------------- geometry
def trajectory(tau, beta, pin, pie):
    """Lens-minus-source separation (theta_E units) in (N, E) components from (tau, beta) and the piE direction."""
    pe = np.hypot(pin, pie)
    pe = np.where(pe < 1e-9, 1e-9, pe)
    en, ee = pin / pe, pie / pe
    return tau * en + beta * ee, tau * ee - beta * en


def centroid_shift(un, ue, fs=1.0, g=0.0):
    """Source light-centroid shift (theta_E units, N and E) for lens-minus-source separation (un, ue).

    fs: source fraction of the unrelated blend at the source's position (astrometric window); g: lens flux / source flux."""
    u2 = un**2 + ue**2
    a = magnification(np.sqrt(u2))
    fs = np.clip(np.asarray(fs, float), 1e-6, 1.0)
    b = (1.0 - fs) / fs
    k = (a * (u2 + 3) / (u2 + 2) + b) / (a + g + b) - (1 + b) / (1 + g + b)
    return -un * k, -ue * k


def shift_amplitude(u, fs=1.0, g=0.0):
    """|delta| / theta_E as a function of |u| (scalar convenience)."""
    dn, de = centroid_shift(np.asarray(u, float), 0.0, fs, g)
    return np.hypot(dn, de)


def blend_offset_profile(a, fs):
    """Time profile h(t) of the centroid pull of a blend offset from the source: delta_b = -b_vec (1-fs) h, with
    h = 1/(A fs + 1 - fs) - 1 (zero at baseline)."""
    fs = np.clip(fs, 1e-6, 1.0)
    return 1.0 / (a * fs + 1 - fs) - 1.0


def parallax_factors(t, ra: float, dec: float, scale: float = 1.0):
    """Absolute parallax factors (N, E) at times t (MJD): the projected Sun position seen from the observer (AU).
    A star of parallax p appears displaced by p * (fN, fE). scale=1.01 approximates Gaia at L2."""
    import astropy.units as u
    from astropy.coordinates import get_body_barycentric
    from astropy.time import Time

    t = np.atleast_1d(np.asarray(t, float))
    a, d = np.radians(ra), np.radians(dec)
    east = np.array([-np.sin(a), np.cos(a), 0.0])
    north = np.array([-np.sin(d) * np.cos(a), -np.sin(d) * np.sin(a), np.cos(d)])
    grid = np.linspace(t.min() - 2, t.max() + 2, max(50, int((t.max() - t.min()) / 2) + 10))
    xyz = -get_body_barycentric("earth", Time(grid, format="mjd")).xyz.to(u.au).value.T * scale
    return np.interp(t, grid, xyz @ north), np.interp(t, grid, xyz @ east)


# ---------------------------------------------------------------- data
@dataclass
class AstroData:
    """Along-scan measurements: one row per CCD observation or per FoV transit.
    t (MJD), theta (scan position angle, rad), w (abscissa, mas), sigma (mas), plx (AL parallax factor; computed if None),
    wclass (optional label per row: Gaia's window class / gate of the transit; each class other than the commonest gets its
    own along-scan offset in both models, so a calibration step between classes, which correlates with magnification for a
    source that crosses G ~ 13 at peak, cannot imitate a deflection)."""
    t: np.ndarray
    theta: np.ndarray
    w: np.ndarray
    sigma: np.ndarray
    plx: np.ndarray | None = None
    wclass: np.ndarray | None = None

    def __post_init__(self):
        self.t, self.theta, self.w, self.sigma = (np.asarray(x, float) for x in (self.t, self.theta, self.w, self.sigma))
        if self.plx is not None:
            self.plx = np.asarray(self.plx, float)
        if self.wclass is not None:
            self.wclass = np.asarray(self.wclass).astype(str)

    def subset(self, m):
        return AstroData(self.t[m], self.theta[m], self.w[m], self.sigma[m], None if self.plx is None else self.plx[m],
                         None if self.wclass is None else self.wclass[m])

    def scaled(self, k: float):
        return AstroData(self.t, self.theta, self.w, self.sigma * k, self.plx, self.wclass)

    def __len__(self):
        return len(self.t)


@dataclass
class PhotData:
    """Flux ratios f (flux / baseline) with errors e at times t (MJD), one series label per point (e.g. "G", "ATLAS_o")."""
    t: np.ndarray
    f: np.ndarray
    e: np.ndarray
    group: np.ndarray

    def __post_init__(self):
        self.t, self.f, self.e = (np.asarray(x, float) for x in (self.t, self.f, self.e))
        self.group = np.asarray(self.group).astype(str)

    def __len__(self):
        return len(self.t)


# ---------------------------------------------------------------- the joint model
@dataclass
class Problem:
    """Joint photometric + along-scan astrometric point-lens model with annual parallax (see module docstring)."""
    phot: PhotData
    astro: AstroData
    ra: float
    dec: float
    t0par: float | None = None
    tref: float = J2017_5
    blend_offset: bool = True
    fs_ast_group: str = "G"
    fs_ast: float | None = None
    lens_flux: float = 0.0                     # g = lens / source flux (0: dark lens)
    fs_bounds: tuple = (0.02, 1.5)
    piE_prior: tuple | None = None            # (piE magnitude, sigma): a photometric constraint from elsewhere
    _cache: dict = field(default_factory=dict, repr=False)

    def __post_init__(self):
        if self.t0par is None:
            self.t0par = float(round(self.phot.t[np.argmax(self.phot.f)])) if len(self.phot) else float(np.median(self.astro.t))
        self.names = sorted(set(self.phot.group.tolist()))
        self.gi = np.array([self.names.index(g) for g in self.phot.group], int)
        self._dn_p, self._de_p = sun_offsets(self.phot.t, self.ra, self.dec, self.t0par) if len(self.phot) else (np.zeros(0),) * 2
        self._dn_a, self._de_a = sun_offsets(self.astro.t, self.ra, self.dec, self.t0par)
        a = self.astro
        if a.plx is None:
            fn, fe = parallax_factors(a.t, self.ra, self.dec, scale=1.01)
            a.plx = fe * np.sin(a.theta) + fn * np.cos(a.theta)
        s, c = np.sin(a.theta), np.cos(a.theta)
        dt = (a.t - self.tref) / YEAR
        self._base = np.column_stack([s, c, dt * s, dt * c, a.plx])      # dalpha*, ddelta, pmra, pmdec, parallax
        # window-class offsets: one along-scan constant per class other than the commonest (>= 3 transits each)
        self._wcols = np.zeros((len(a.t), 0))
        self.wclasses: list[str] = []
        if a.wclass is not None:
            labs, cnt = np.unique(a.wclass, return_counts=True)
            if len(labs) > 1:
                ref = labs[np.argmax(cnt)]
                self.wclasses = [lb for lb, n in zip(labs, cnt, strict=True) if lb != ref and n >= 3]
                if self.wclasses:
                    self._wcols = np.column_stack([(a.wclass == lb).astype(float) for lb in self.wclasses])
        self._sin, self._cos = s, c
        self._wa = 1.0 / a.sigma
        self._wp = 1.0 / self.phot.e if len(self.phot) else np.zeros(0)

    # -- pieces
    def _uv(self, q, which: str):
        t0, te, u0, pin, pie = q
        t, dn, de = ((self.phot.t, self._dn_p, self._de_p) if which == "p" else (self.astro.t, self._dn_a, self._de_a))
        tau = (t - t0) / te + pin * dn + pie * de
        beta = u0 + (-pin * de + pie * dn)
        return tau, beta

    def phot_solve(self, q):
        """Per-series fs (closed form, clipped to fs_bounds) and the photometric model."""
        if not len(self.phot):
            return np.zeros(0), np.zeros(0)
        tau, beta = self._uv(q, "p")
        a = magnification(np.hypot(tau, beta))
        x = a - 1.0
        y = self.phot.f - 1.0
        w2 = self._wp**2
        fs = np.empty(len(self.names))
        for k in range(len(self.names)):
            m = self.gi == k
            den = np.sum(w2[m] * x[m] ** 2)
            fs[k] = np.sum(w2[m] * x[m] * y[m]) / den if den > 0 else 1.0
        fs = np.clip(fs, *self.fs_bounds)
        return fs, fs[self.gi] * x + 1.0

    def fs_astrometric(self, fs_phot) -> float:
        if self.fs_ast is not None:
            return float(min(self.fs_ast, 1.0))
        if self.fs_ast_group in self.names:
            return float(min(fs_phot[self.names.index(self.fs_ast_group)], 1.0))
        return 1.0

    def astro_columns(self, q, fs_ast):
        """Design matrix: base (5) + deflection per unit theta_E (1) + blend-offset pull (2 if blend_offset)."""
        tau, beta = self._uv(q, "a")
        un, ue = trajectory(tau, beta, q[3], q[4])
        dn, de = centroid_shift(un, ue, fs_ast, self.lens_flux)
        cols = [self._base, (de * self._sin + dn * self._cos)[:, None]]
        if self.blend_offset:
            h = blend_offset_profile(magnification(np.hypot(un, ue)), fs_ast)
            cols.append(np.column_stack([h * self._sin, h * self._cos]))
        if self._wcols.shape[1]:
            cols.append(self._wcols)
        return np.hstack(cols)

    def astro_solve(self, X, theta_e: float | None):
        """Weighted linear solve. theta_e None: free and >= 0; a number: fixed (0 = no deflection)."""
        w = self._wa
        y = self.astro.w
        idx = 5
        if theta_e is None:
            beta, *_ = np.linalg.lstsq(X * w[:, None], y * w, rcond=None)
            if beta[idx] >= 0:
                return beta
            theta_e = 0.0
        keep = [i for i in range(X.shape[1]) if i != idx]
        yy = y - theta_e * X[:, idx]
        b2, *_ = np.linalg.lstsq(X[:, keep] * w[:, None], yy * w, rcond=None)
        beta = np.empty(X.shape[1])
        beta[keep] = b2
        beta[idx] = theta_e
        return beta

    def residuals(self, q, theta_e=None, full: bool = False):
        """Whitened residuals. theta_e: None (free, >= 0), a number (fixed), or a function of q (e.g. a fixed mass:
        theta_E = kappa M |piE|)."""
        if callable(theta_e):
            theta_e = float(theta_e(q))
        fs, fmod = self.phot_solve(q)
        rp = (fmod - self.phot.f) * self._wp
        fa = self.fs_astrometric(fs)
        X = self.astro_columns(q, fa)
        beta = self.astro_solve(X, theta_e)
        ra = (X @ beta - self.astro.w) * self._wa
        r = np.concatenate([rp, ra])
        if self.piE_prior is not None:
            r = np.append(r, (np.hypot(q[3], q[4]) - self.piE_prior[0]) / self.piE_prior[1])
        if full:
            return r, dict(fs=fs, fs_ast=fa, lin=beta, X=X)
        return r

    def bounds(self, t0c: float):
        lo = np.array([t0c - 400, 1.0, -3.0, -5.0, -5.0])
        hi = np.array([t0c + 400, 3000.0, 3.0, 5.0, 5.0])
        return lo, hi

    def starts(self, t0c: float, te_hint: float | None = None):
        tes = (te_hint,) if te_hint else (30.0, 100.0, 300.0)
        for te in tes:
            for u0 in (0.3, -0.3):
                for pi in ((0.1, 0.1), (-0.1, -0.1)):
                    yield np.array([t0c, te, u0, *pi])

    def fit(self, theta_e: float | None = None, t0c: float | None = None, starts=None, te_hint: float | None = None):
        """Best fit with theta_E free (None) or fixed. Returns dict(q, chi2, fs, fs_ast, lin, theta_e)."""
        if t0c is None:
            t0c = float(self.phot.t[np.argmax(self.phot.f)]) if len(self.phot) else float(np.median(self.astro.t))
        lo, hi = self.bounds(t0c)
        best = None
        for q0 in (starts if starts is not None else self.starts(t0c, te_hint)):
            q0 = np.clip(np.asarray(q0, float), lo + 1e-6, hi - 1e-6)
            try:
                r = least_squares(lambda q: self.residuals(q, theta_e), q0, bounds=(lo, hi), x_scale="jac", max_nfev=400)
            except (ValueError, np.linalg.LinAlgError):
                continue
            if best is None or r.cost < best.cost:
                best = r
        q = best.x
        res, info = self.residuals(q, theta_e, full=True)
        return dict(q=q, chi2=float(res @ res), theta_e=float(info["lin"][5]), **info)

    @property
    def n_data(self) -> int:
        return len(self.phot) + len(self.astro)

    def n_params(self, theta_free: bool = True) -> int:
        return 5 + len(self.names) + 5 + int(theta_free) + (2 if self.blend_offset else 0) + len(self.wclasses)

    @property
    def n_astro_linear(self) -> int:
        return 5 + 1 + (2 if self.blend_offset else 0) + len(self.wclasses)


# ---------------------------------------------------------------- fitting a target
def _jacobian(fun, x, rel=1e-5):
    f0 = fun(x)
    J = np.empty((f0.size, x.size))
    for i in range(x.size):
        h = rel * max(abs(x[i]), 1.0)
        xp = x.copy()
        xp[i] += h
        J[:, i] = (fun(xp) - f0) / h
    return J


def covariance(prob: Problem, res: dict) -> tuple[np.ndarray, list[str]]:
    """Covariance of (q, theta_E) at a best fit, from the Jacobian of the whitened residuals with the other linear
    parameters re-solved at each step (i.e. profiled), by finite differences."""
    x0 = np.r_[res["q"], res["theta_e"]]

    def fun(x):
        return prob.residuals(x[:5], theta_e=float(x[5]))

    J = _jacobian(fun, x0)
    C = np.linalg.pinv(J.T @ J)
    return C, ["t0", "tE", "u0", "piE_N", "piE_E", "theta_E"]


def mass_samples(q, theta_e, C, n=20000, rng=None):
    """Lens mass (Msun) Monte Carlo from the (q, theta_E) covariance: M = theta_E / (kappa |piE|)."""
    rng = np.random.default_rng(0) if rng is None else rng
    x = rng.multivariate_normal(np.r_[q, theta_e], C, size=n, check_valid="ignore")
    pe = np.hypot(x[:, 3], x[:, 4])
    th = x[:, 5]
    ok = (pe > 0) & (th > 0)
    return th[ok] / (KAPPA * pe[ok]), ok.mean()


def theta_e_upper_limit(prob: Problem, res_free: dict, level: float = 2.706, hi: float | None = None, iters: int = 12):
    """One-sided upper limit on theta_E (Delta chi^2 = 2.706: 95%), profiling q (refit from the best q at each value)."""
    q0 = res_free["q"]
    c0 = res_free["chi2"]
    t0c = float(q0[0])

    def dchi(th):
        return prob.fit(theta_e=th, t0c=t0c, starts=[q0, q0 * np.array([1, 1.3, 1, 1, 1]), q0 * np.array([1, 0.7, 1, 1, 1])])["chi2"] - c0

    lo = max(res_free["theta_e"], 0.0)
    hi = hi or max(4 * lo, 1.0)
    for _ in range(8):
        if dchi(hi) >= level:
            break
        lo, hi = hi, hi * 3
    else:
        return float("inf")
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if dchi(mid) < level:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def mass_profile(prob: Problem, res_free: dict, m_lo: float = 0.01, m_hi: float = 1000.0, n: int = 21, iters: int = 8):
    """Profile likelihood of the lens mass: at fixed M, theta_E = kappa M |piE| and q is refitted. Returns the best mass,
    68% (Delta chi^2 = 1) and 95% (3.84) two-sided intervals, the one-sided 95% upper limit (2.706), Delta chi^2 at
    M = 3 Msun, and flags where an interval runs off the scanned range [m_lo, m_hi] (unbounded by the data)."""
    q0 = np.asarray(res_free["q"], float)
    pe0 = max(np.hypot(q0[3], q0[4]), 1e-6)
    unit = q0[3:5] / pe0
    th0 = res_free["theta_e"]
    t0c = float(q0[0])
    cache: dict[float, float] = {}

    def chi(lm):
        lm = round(float(lm), 6)
        if lm in cache:
            return cache[lm]
        m = 10**lm
        starts = [q0]
        if th0 > 0:
            starts.append(np.r_[q0[:3], unit * th0 / (KAPPA * m)])
        r = prob.fit(theta_e=lambda q, m=m: KAPPA * m * np.hypot(q[3], q[4]), t0c=t0c, starts=starts)
        cache[lm] = r["chi2"]
        return r["chi2"]

    grid = np.linspace(np.log10(m_lo), np.log10(m_hi), n)
    vals = np.array([chi(g) for g in grid])
    i = int(np.argmin(vals))
    lo_b, hi_b = grid[max(i - 1, 0)], grid[min(i + 1, n - 1)]
    for _ in range(iters):                      # golden-ish refinement of the minimum
        a, b = lo_b + (hi_b - lo_b) / 3, hi_b - (hi_b - lo_b) / 3
        if chi(a) < chi(b):
            hi_b = b
        else:
            lo_b = a
    lbest = 0.5 * (lo_b + hi_b)
    cmin = min(chi(lbest), vals.min())

    def crossing(level, side):
        g = grid[grid < lbest][::-1] if side < 0 else grid[grid > lbest]
        inside = lbest
        for x in g:
            if chi(x) - cmin >= level:
                outside = x
                break
            inside = x
        else:
            return (m_lo if side < 0 else m_hi), True
        for _ in range(iters):
            mid = 0.5 * (inside + outside)
            if chi(mid) - cmin < level:
                inside = mid
            else:
                outside = mid
        return 10 ** (0.5 * (inside + outside)), False

    out = dict(M_best=float(10**lbest), dchi2_at_M3=float(chi(np.log10(3.0)) - cmin), chi2_min_mass=float(cmin))
    for tag, lev in (("68", 1.0), ("95", 3.841)):
        lo, olo = crossing(lev, -1)
        hi, ohi = crossing(lev, +1)
        out.update({f"M_lo{tag}": float(lo), f"M_hi{tag}": float(hi), f"M_lo{tag}_open": olo, f"M_hi{tag}_open": ohi})
    ul, oul = crossing(2.706, +1)
    out.update(M_ul95=float(ul) if not oul else float("inf"), M_ul95_open=oul)
    out["M_gt3_sigma"] = float(np.sqrt(max(out["dchi2_at_M3"], 0.0))) if out["M_best"] > 3 else 0.0
    return out


def fit_target(phot: PhotData, astro: AstroData, ra: float, dec: float, *, t0c=None, te_hint=None, piE_prior=None,
               blend_offset=True, rescale=True, clip=5.0, robust_k=6.0, max_clip_frac=0.10, upper_limit=True,
               profile_mass=True, rng=None, **kw) -> dict:
    """Fit a target: deflection model vs no deflection, theta_E, piE, M with uncertainties, and the likelihood-ratio test.

    Outliers, in three steps:
      1. robust pass: the point furthest from a position + proper motion + parallax fit (which cannot bend to one point)
         is removed if the deflection model fitted without it still misses it by more than robust_k x the robust sigma
         (1.4826 MAD, floored at 1); repeat. Testing the deleted residual protects a real deflection (its points are
         predicted by their neighbours) and catches a wild value (DR4 has values outside the window) that a short,
         strong lens or a tiny bump times a huge blend offset would otherwise absorb;
      2. rescale: inflate the errors by sqrt(chi2/dof) when that exceeds 1.2 (as RUWE does);
      3. clip: drop the largest residual if beyond `clip` sigma, also as a deleted residual, one point at a time, at most
         max_clip_frac of the points.
    The returned fit, the null fit and every statistic use exactly the points kept at the end.
    Mass: M_med/M_16/M_84 from the (q, theta_E) covariance (Gaussian; too narrow when piE is weakly constrained) and, the
    numbers to quote, the profile-likelihood M_best, M_lo68/M_hi68, M_lo95/M_hi95, M_ul95 and the significance of M > 3 Msun.
    Returns a flat dict (json-friendly)."""
    keep = np.ones(len(astro), bool)
    scale = 1.0
    nph = len(phot)

    def build():
        a = astro.subset(keep).scaled(scale)
        prob = Problem(phot, a, ra, dec, blend_offset=blend_offset, piE_prior=piE_prior, **kw)
        alt = prob.fit(None, t0c=t0c, te_hint=te_hint)
        r = prob.residuals(alt["q"])[nph:nph + len(a)]
        return a, prob, alt, r

    def null_fit(prob, alt):
        nl = prob.fit(0.0, t0c=t0c, starts=[alt["q"]] + list(prob.starts(float(alt["q"][0]), te_hint))[:2])
        return prob.residuals(nl["q"], theta_e=0.0)[nph:nph + len(prob.astro)], nl["q"]

    def deleted_resid(a, j, q_start):
        """Residual of point j (in its own sigma) predicted by the deflection model fitted without it. The fit starts from
        the no-deflection trajectory and the photometric starts, never from a trajectory that may have bent to fit j."""
        b = AstroData(a.t, a.theta, a.w, a.sigma.copy(), a.plx, a.wclass)
        b.sigma[j] *= 1e6
        pr = Problem(phot, b, ra, dec, blend_offset=blend_offset, piE_prior=piE_prior, **kw)
        f = pr.fit(None, t0c=t0c, starts=[q_start] + list(pr.starts(float(t0c if t0c is not None else q_start[0]), te_hint)))
        return float(pr.residuals(f["q"])[nph + j] * 1e6)

    def mad(x):
        return max(1.4826 * float(np.median(np.abs(x - np.median(x)))), 1.0)

    a, prob, alt, r = build()
    n_robust = 0
    for _ in range(12):
        # 1. robust pass. The candidate is the point that departs most from the NO-deflection model: a lone wild value
        # can hijack the deflection model (a short, strong lens fits one point), so its residual there is small.
        # It is removed only if the deflection model fitted without it still misses it by > robust_k robust sigma
        # (a deleted residual): a point that belongs to a real deflection is predicted by its neighbours and stays.
        # candidate: the largest residual from position + proper motion + parallax (+ window classes) alone, which cannot
        # bend to fit a single point (the deflection and blend-offset terms can: a short lens, a tiny bump times a huge
        # offset)
        Xb = np.hstack([prob._base, prob._wcols]) / a.sigma[:, None]
        cb, *_ = np.linalg.lstsq(Xb, a.w / a.sigma, rcond=None)
        rb = Xb @ cb - a.w / a.sigma
        j = int(np.argmax(np.abs(rb)))
        if abs(rb[j]) <= robust_k * mad(rb) or keep.sum() <= 10:
            break
        q0 = null_fit(prob, alt)[1]
        if abs(deleted_resid(a, j, q0)) <= robust_k * mad(r):
            break
        keep[np.flatnonzero(keep)[j]] = False
        n_robust += 1
        a, prob, alt, r = build()
    dof = max(len(a) - prob.n_astro_linear, 1)          # 2. error rescaling
    s2 = float(r @ r) / dof
    if rescale and s2 > 1.2:
        scale = float(np.sqrt(s2))
        a, prob, alt, r = build()
    n_clip = 0                                          # 3. one point at a time, on deleted residuals
    max_clip = max(2, int(max_clip_frac * len(astro)))
    while clip and n_clip < max_clip:
        j = int(np.argmax(np.abs(r)))
        if abs(r[j]) <= clip or abs(deleted_resid(a, j, null_fit(prob, alt)[1])) <= clip:
            break
        keep[np.flatnonzero(keep)[j]] = False
        n_clip += 1
        a, prob, alt, r = build()
    null = prob.fit(0.0, t0c=t0c, starts=[alt["q"]] + list(prob.starts(float(alt["q"][0]), te_hint)))
    if null["chi2"] < alt["chi2"]:  # theta_E = 0 is inside the alternative: refit it from the null's q
        alt2 = prob.fit(None, starts=[null["q"]], t0c=t0c)
        if alt2["chi2"] < alt["chi2"]:
            alt = alt2
    dchi2 = max(null["chi2"] - alt["chi2"], 0.0)
    out = dict(n_astro=int(len(a)), n_astro_clipped=int((~keep).sum()), n_robust_rejected=n_robust, n_sigma_clipped=n_clip,
               max_abs_resid=float(np.max(np.abs(r))) if len(r) else 0.0, n_window_classes=len(prob.wclasses) + 1,
               n_phot=int(len(phot)), err_scale=float(scale),
               chi2_alt=alt["chi2"], chi2_null=null["chi2"], dchi2=dchi2,
               p_null_asymptotic=float(0.5 * chi2_dist.sf(dchi2, 1)) if dchi2 > 0 else 1.0,
               t0=float(alt["q"][0]), tE=float(alt["q"][1]), u0=float(alt["q"][2]), piE_N=float(alt["q"][3]),
               piE_E=float(alt["q"][4]), piE=float(np.hypot(alt["q"][3], alt["q"][4])), theta_e=alt["theta_e"],
               fs_ast=alt["fs_ast"], fs={k: float(v) for k, v in zip(prob.names, alt["fs"], strict=True)},
               pm_ra=float(alt["lin"][2]), pm_dec=float(alt["lin"][3]), parallax=float(alt["lin"][4]))
    try:
        C, _ = covariance(prob, alt)
        out["sig_theta_e"] = float(np.sqrt(max(C[5, 5], 0)))
        # sigma of |piE| (absolute), by the delta method
        sp = np.sqrt(max((alt["q"][3] ** 2 * C[3, 3] + alt["q"][4] ** 2 * C[4, 4] + 2 * alt["q"][3] * alt["q"][4] * C[3, 4]), 0))
        out["sig_piE"] = float(sp / max(out["piE"], 1e-9))
        out["sig_tE"] = float(np.sqrt(max(C[1, 1], 0)))
        if alt["theta_e"] > 0:
            m, frac = mass_samples(alt["q"], alt["theta_e"], C, rng=rng)
            if len(m) > 100:
                out.update(M_med=float(np.median(m)), M_16=float(np.percentile(m, 16)), M_84=float(np.percentile(m, 84)),
                           M_2p5=float(np.percentile(m, 2.5)), M_97p5=float(np.percentile(m, 97.5)), M_valid_frac=float(frac))
    except (np.linalg.LinAlgError, ValueError) as e:
        out["cov_error"] = str(e)[:200]
    if upper_limit:
        try:
            ul = theta_e_upper_limit(prob, alt)
            out["theta_e_ul95"] = float(ul)
            pe_lo = max(out["piE"] - 2 * out.get("sig_piE", np.inf), 0.0)
            out["M_ul95_at_piE"] = float(ul / (KAPPA * out["piE"])) if out["piE"] > 0 else float("inf")
            out["M_ul95_at_piE_minus2sig"] = float(ul / (KAPPA * pe_lo)) if pe_lo > 0 else float("inf")
        except (np.linalg.LinAlgError, ValueError) as e:
            out["ul_error"] = str(e)[:200]
    if profile_mass:
        try:
            out.update(mass_profile(prob, alt))
        except (np.linalg.LinAlgError, ValueError) as e:
            out["mass_profile_error"] = str(e)[:200]
    return out


# ---------------------------------------------------------------- expected signals (fast, no noise)
def expected_dchi2(t, theta, sigma, plx, ra, dec, q, theta_e, fs_ast=1.0, t0par=None, tref=J2017_5, blend_offset=True,
                   _offsets=None):
    """Noise-free ("Asimov") Delta chi^2 of the deflection against the no-deflection model with the trajectory known:
    theta_E^2 times the squared norm of the whitened deflection template after projecting out position, proper motion,
    parallax and (if blend_offset) the blend-offset pull. Vectorised over samples: q is (n, 5), theta_e and fs_ast (n,).
    Returns (dchi2 (n,), sigma_theta_e (n,)) with the trajectory known."""
    q = np.atleast_2d(np.asarray(q, float))
    n = q.shape[0]
    theta_e = np.broadcast_to(np.asarray(theta_e, float), (n,))
    fs_ast = np.broadcast_to(np.asarray(fs_ast, float), (n,))
    t = np.asarray(t, float)
    if _offsets is None:
        t0par = float(np.median(q[:, 0])) if t0par is None else t0par
        _offsets = sun_offsets(t, ra, dec, t0par)
    dn_s, de_s = _offsets
    s, c = np.sin(theta), np.cos(theta)
    w = 1.0 / np.asarray(sigma, float)
    dt = (t - tref) / YEAR
    B = np.column_stack([s, c, dt * s, dt * c, plx]) * w[:, None]
    Q, _ = np.linalg.qr(B)
    tau = (t[None, :] - q[:, :1]) / q[:, 1:2] + q[:, 3:4] * dn_s + q[:, 4:5] * de_s
    beta = q[:, 2:3] + (-q[:, 3:4] * de_s + q[:, 4:5] * dn_s)
    un, ue = trajectory(tau, beta, q[:, 3:4], q[:, 4:5])
    dn, de = centroid_shift(un, ue, fs_ast[:, None])
    S = (de * s + dn * c) * w
    S = S - (S @ Q) @ Q.T
    fisher = np.einsum("ij,ij->i", S, S)
    if blend_offset:
        h = blend_offset_profile(magnification(np.hypot(un, ue)), fs_ast[:, None])
        H = np.stack([h * s * w, h * c * w], axis=2)                     # (n, m, 2)
        H = H - np.einsum("nmk,mj,lj->nlk", H, Q, Q)
        HtH = np.einsum("nmk,nml->nkl", H, H) + 1e-12 * np.eye(2)
        HtS = np.einsum("nmk,nm->nk", H, S)
        sol = np.linalg.solve(HtH, HtS[..., None])[..., 0]
        fisher = fisher - np.einsum("nk,nk->n", HtS, sol)
    fisher = np.maximum(fisher, 0.0)
    return theta_e**2 * fisher, np.where(fisher > 0, 1.0 / np.sqrt(np.maximum(fisher, 1e-300)), np.inf)


def detection_probability(lam, threshold: float = 25.0):
    """P(Delta chi^2 >= threshold) for a one-parameter test with noncentrality lam (noncentral chi^2, 1 dof)."""
    from scipy.stats import ncx2
    lam = np.asarray(lam, float)
    return np.where(lam > 0, ncx2.sf(threshold, 1, np.maximum(lam, 1e-12)), chi2_dist.sf(threshold, 1))


# ---------------------------------------------------------------- simulation
def simulate(t, theta, plx, ra, dec, G, q, theta_e, *, fs=1.0, pm=(0.0, 0.0), parallax=0.0, sig_scale=1.0,
             blend_vec=(0.0, 0.0), precision="edr3", rng=None, t0par=None, phot_extra: PhotData | None = None,
             wclass_step: float | None = None, wclass_g: float = 13.0):
    """Simulated Gaia data for one target: per-FoV-transit along-scan abscissae with EDR3-like errors, and Gaia G flux
    ratios at the same transits. q = (t0, tE, u0, piE_N, piE_E) (geocentric at t0par), theta_e in mas (0: no lens).
    blend_vec: (N, E) offset (mas) of the blend light centroid from the source, times (1 - fs) (the pull's amplitude).
    wclass_step: if given, transits brighter than wclass_g (magnified) are labelled window class "bright" and shifted by
    this many mas along scan (a calibration step between window classes); the labels are attached to the AstroData."""
    rng = np.random.default_rng() if rng is None else rng
    t = np.asarray(t, float)
    theta = np.asarray(theta, float)
    t0par = float(round(q[0])) if t0par is None else t0par
    dn_s, de_s = sun_offsets(t, ra, dec, t0par)
    tau = (t - q[0]) / q[1] + q[3] * dn_s + q[4] * de_s
    beta = q[2] + (-q[3] * de_s + q[4] * dn_s)
    un, ue = trajectory(tau, beta, q[3], q[4])
    a = magnification(np.hypot(un, ue))
    sig = sigma_al_fov(np.full(t.shape, G) - 2.5 * np.log10(fs * a + 1 - fs), precision) * sig_scale
    dn, de = centroid_shift(un, ue, fs)
    h = blend_offset_profile(a, fs)
    s, c = np.sin(theta), np.cos(theta)
    dt = (t - J2017_5) / YEAR
    w = (pm[0] * dt * s + pm[1] * dt * c + parallax * plx + theta_e * (de * s + dn * c)
         - h * (blend_vec[1] * s + blend_vec[0] * c))
    w = w + rng.normal(0, sig)
    labels = None
    if wclass_step is not None:
        bright = (G - 2.5 * np.log10(fs * a + 1 - fs)) < wclass_g
        w = w + wclass_step * bright
        labels = np.where(bright, "bright", "faint")
    astro = AstroData(t, theta, w, sig, plx, labels)
    f = fs * a + 1 - fs
    sg = sigma_g_transit(G - 2.5 * np.log10(f)) * f / 1.0857
    ft = f + rng.normal(0, sg)
    phot = PhotData(t, ft, sg, np.array(["G"] * len(t)))
    if phot_extra is not None:
        phot = PhotData(np.r_[phot.t, phot_extra.t], np.r_[phot.f, phot_extra.f], np.r_[phot.e, phot_extra.e],
                        np.r_[phot.group, phot_extra.group])
    return phot, astro
