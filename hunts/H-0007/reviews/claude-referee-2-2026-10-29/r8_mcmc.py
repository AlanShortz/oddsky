"""Referee 2, attack 4: honest uncertainties. emcee on the parallax model, walkers started in BOTH u0 modes.
Runs: A investigators' error model, errors scaled to chi2/dof = 1; B + free 02a zero-point scale; C fitted fractional
jitter; D = A with an extra x1.47 for lag-1 correlated residuals (rho = 0.37 -> sqrt((1+rho)/(1-rho))).
uv run --with emcee python .../r8_mcmc.py"""
import sys, json, numpy as np, emcee
sys.path.insert(0, "hunts/H-0007/reviews/claude-referee-2-2026-10-29")
import r2_lib as L
from r4_fits import fit, par_both

d = L.nightly(L.load_raw())
t, f, e0 = d.mjd.values, d.f.values, d.e.values
geo = L.Geo(t)
is02 = d.unit.values == "02a"
ahat = geo.acc / np.linalg.norm(geo.acc)
KAPPA, PIS = 8.144, 0.330


def A_par(p):
    tau, beta = L.traj_par(t, geo, *p[:5])
    return L.pacz(np.hypot(tau, beta))


def run(tag, scale02=False, jitter=False, efac=1.0, nsteps=6000):
    best = {s: fit(d, "par", u0sign=s, scale_units=("02a",) if scale02 else (),
                   starts=[[58012, 47.7, s * 0.14, -1, -0.37], [58012, 47.7, s * 0.14, -0.6, -0.46], [58012, 47.7, s * 0.14, 0.9, -0.4]])
            for s in (1, -1)}
    k = 5 + scale02
    chi2min = min(b["chi2"] for b in best.values())
    s_err = np.sqrt(chi2min / (len(t) - k)) if not jitter else 1.0
    e = e0 * s_err * efac
    lo = np.r_[57990, 5, -2, -4, -4, [0.9] * scale02, [0] * jitter]
    hi = np.r_[58030, 300, 2, 4, 4, [1.1] * scale02, [0.1] * jitter]

    def lnp(p):
        if np.any(p < lo) or np.any(p > hi):
            return -np.inf
        m = A_par(p)
        if scale02:
            m = np.where(is02, m * p[5], m)
        if jitter:
            ee = np.hypot(e, p[-1] * f)
            return -0.5 * np.sum(((m - f) / ee) ** 2 + 2 * np.log(ee))
        return -0.5 * np.sum(((m - f) / e) ** 2)

    nw, nd = 48, k + jitter
    rng = np.random.default_rng(7)
    start = []
    for i in range(nw):
        b = best[1 if i % 2 == 0 else -1]["p"]
        q = np.r_[b, [0.005] * jitter] + 1e-3 * rng.standard_normal(nd)
        start.append(q)
    S = emcee.EnsembleSampler(nw, nd, lnp)
    S.run_mcmc(np.array(start), nsteps, progress=False)
    ch = S.get_chain(discard=nsteps // 3, thin=10, flat=True)
    piN, piE_ = ch[:, 3], ch[:, 4]
    piE = np.hypot(piN, piE_)
    par = piN * ahat[0] + piE_ * ahat[1]; perp = -piN * ahat[1] + piE_ * ahat[0]
    Amax = L.pacz(np.abs(ch[:, 2]))
    pct = lambda x: np.round(np.percentile(x, [2.5, 16, 50, 84, 97.5]), 3).tolist()
    out = {"tag": tag, "error_scale": round(float(s_err * efac), 3), "chi2min": {int(s): round(b["chi2"], 1) for s, b in best.items()},
           "frac_u0_pos": round(float(np.mean(ch[:, 2] > 0)), 3), "tE": pct(ch[:, 1]), "u0": pct(ch[:, 2]), "piE_N": pct(piN), "piE_E": pct(piE_),
           "piE": pct(piE), "pi_par": pct(par), "pi_perp": pct(perp), "Amax": pct(Amax),
           "P(piE<0.5)": round(float(np.mean(piE < 0.5)), 4), "P(piE<0.7)": round(float(np.mean(piE < 0.7)), 4)}
    if scale02:
        out["scale02"] = pct(ch[:, 5])
    if jitter:
        out["jitter"] = pct(ch[:, -1])
    # lens mass at DL = 0.5, 1, 2 kpc
    for DL in (0.5, 1.0, 2.0):
        out[f"M(DL={DL})"] = pct((1 / DL - PIS) / (KAPPA * piE**2))
    print(json.dumps(out), flush=True)
    return out


if __name__ == "__main__":
    res = [run("A: scaled errors", ), run("B: + 02a scale", scale02=True), run("C: fitted jitter", jitter=True),
           run("D: scaled + correlated-noise x1.47", efac=1.47), run("E: 02a scale + x1.47", scale02=True, efac=1.47)]
    json.dump(res, open("hunts/H-0007/reviews/claude-referee-2-2026-10-29/r8_mcmc.json", "w"), indent=1)
