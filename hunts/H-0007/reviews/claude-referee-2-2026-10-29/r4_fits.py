"""Referee 2, attacks 1-2: independent refits. Static, parallax (both u0 signs), generic acceleration(+jerk);
piE grid (ecliptic and jerk-parallax degeneracies); systematics variants (saturation cut, unit offsets, per-unit
baselines, no NEOWISE, single unit, chi_n cut, jackknife by night, window). Run from repo root:
uv run python hunts/H-0007/reviews/claude-referee-2-2026-10-29/r4_fits.py [--grid] [--jack]"""
import sys, json, numpy as np, pandas as pd
from scipy.optimize import least_squares
sys.path.insert(0, "hunts/H-0007/reviews/claude-referee-2-2026-10-29")
import r2_lib as L

RAW = L.load_raw()
_g = L.Geo(np.array([58011.0])); A_HAT = _g.acc / np.linalg.norm(_g.acc)  # projected Sun acceleration direction (N, E)
OUT = "hunts/H-0007/reviews/claude-referee-2-2026-10-29/"


def fit(d, kind, fs_free=False, scale_units=(), fixed=None, starts=None, u0sign=0):
    t, f, e = d.mjd.values, d.f.values, d.e.values
    geo = L.Geo(t)
    bands = [b for b in ("c", "o") if fs_free and (d.band == b).any()]
    nfs, nsc = len(bands), len(scale_units)

    def A_of(p):
        if kind == "static":
            tau, beta = L.traj_static(t, *p[:3])
        elif kind == "par":
            piN, piE = (fixed if fixed is not None else p[3:5])
            tau, beta = L.traj_par(t, geo, p[0], p[1], p[2], piN, piE)
        elif kind == "acc":
            tau, beta = L.traj_acc(t, *p[:5])
        elif kind == "accjerk":
            tau, beta = L.traj_acc(t, *p[:7])
        return L.pacz(np.hypot(tau, beta))

    nk = {"static": 3, "par": 5 if fixed is None else 3, "acc": 5, "accjerk": 7}[kind]

    def model(p):
        A = A_of(p)
        fs = {b: p[nk + i] for i, b in enumerate(bands)}
        sc = {un: p[nk + nfs + i] for i, un in enumerate(scale_units)}
        return L.flux(A, d, fs, sc)

    best = None
    for s in (starts or [[58011, 47, u0] for u0 in (0.05, 0.14, 0.3, -0.05, -0.14, -0.3)]):
        p0 = list(s) + {"static": [], "par": [-0.5, -0.3] if fixed is None else [], "acc": [0, 0], "accjerk": [0, 0, 0, 0]}[kind][: nk - len(s)]
        p0 = p0[:nk] + [1.0] * nfs + [1.0] * nsc
        lo = [57990, 5, -2] + [-5] * (nk - 3) + [0.05] * nfs + [0.8] * nsc
        hi = [58030, 300, 2] + [5] * (nk - 3) + [1.5] * nfs + [1.2] * nsc
        if kind == "static" or u0sign > 0:
            lo[2] = 1e-4
            if s[2] < 0:
                continue
        if u0sign < 0:
            hi[2] = -1e-4
            if s[2] > 0:
                continue
        r = least_squares(lambda p: (model(p) - f) / e, p0, bounds=(lo, hi), x_scale="jac")
        if best is None or r.cost < best.cost:
            best = r
    chi2 = 2 * best.cost
    try:
        cov = np.linalg.inv(best.jac.T @ best.jac)
        err = np.sqrt(np.diag(cov))
    except np.linalg.LinAlgError:
        err = np.full(len(best.x), np.nan)
    return dict(p=best.x, err=err, chi2=chi2, n=len(t), k=len(best.x), model=model(best.x), A=A_of(best.x))


def par_both(d, **kw):
    """Best parallax fit for u0 > 0 and u0 < 0 separately."""
    out = {}
    for sgn in (+1, -1):
        st = [[58011, 47, sgn * u0] + pi for u0 in (0.05, 0.14, 0.3) for pi in ([-1, -0.4], [0.5, 0.3], [0, 0], [1, -0.4], [-1, 0.4])]
        out[sgn] = fit(d, "par", starts=st, u0sign=sgn, **kw)
        # enforce sign
    return out


def summarise(tag, d, extra=None, **kw):
    s = fit(d, "static", **kw)
    pb = par_both(d, **kw)
    pp = min(pb.values(), key=lambda r: r["chi2"])
    p = pp["p"]; piE = np.hypot(p[3], p[4])
    row = dict(variant=tag, N=s["n"], chi2_static=round(s["chi2"], 1), chi2_par=round(pp["chi2"], 1),
               dchi2=round(s["chi2"] - pp["chi2"], 1), chi2_par_other_u0=round(max(pb.values(), key=lambda r: r["chi2"])["chi2"], 1),
               t0=round(p[0], 2), tE=round(p[1], 2), u0=round(p[2], 3), piE_N=round(p[3], 3), piE_E=round(p[4], 3),
               piE=round(piE, 3), sig_piE=round(float(np.hypot(p[3] * pp["err"][3], p[4] * pp["err"][4]) / piE), 3),
               Amax=round(float(L.pacz(abs(p[2]))), 2))
    if extra:
        row.update(extra(pp, d))
    return row, s, pp


if __name__ == "__main__":
    rows = []
    base = L.nightly(RAW)
    r0, s0, p0 = summarise("baseline (replicates investigators' choices)", base)
    rows.append(r0)
    print(pd.DataFrame([r0]).T)
    # out-of-sample peak nights
    for sat_tag, mjd in (("58007.6 (02a)", 58007.6), ("58009.6 (01a)", 58009.59)):
        pass
    pk = L.nightly(RAW, sat=None)
    pk = pk[(pk.mjd > 58005) & (pk.mjd < 58011) & (pk.band == "o")]
    g = L.Geo(pk.mjd.values)
    for nm, r in (("static", s0), ("parallax", p0)):
        p = r["p"]
        if nm == "static":
            A = L.pacz(np.hypot(*L.traj_static(pk.mjd.values, *p[:3])))
        else:
            A = L.pacz(np.hypot(*L.traj_par(pk.mjd.values, g, *p[:5])))
        print(f"out-of-sample {nm}: " + ", ".join(f"MJD {m:.2f} obs {o:.2f} pred {a:.2f}" for m, o, a in zip(pk.mjd, pk.f, A)))
    # degeneracies: other u0 sign is in the table; acceleration models
    for kind in ("acc", "accjerk"):
        r = fit(base, kind)
        print(f"{kind}: chi2 {r['chi2']:.1f} (k={r['k']}); params {np.round(r['p'], 3).tolist()}")
        rows.append(dict(variant=f"generic {kind} model", N=r["n"], chi2_par=round(r["chi2"], 1), dchi2=round(s0["chi2"] - r["chi2"], 1)))
    # systematics variants
    V = [("sat cut m > 11.8 (adds 58007)", dict(d=L.nightly(RAW, sat=11.8))),
         ("sat cut none (adds 58007, 58009)", dict(d=L.nightly(RAW, sat=None))),
         ("sat cut m > 12.5", dict(d=L.nightly(RAW, sat=12.5))),
         ("sat cut m > 13.0", dict(d=L.nightly(RAW, sat=13.0))),
         ("no NEOWISE", dict(d=L.nightly(RAW, neowise=False))),
         ("per-unit baselines", dict(d=L.nightly(RAW, per_unit_base=True))),
         ("02a scale free", dict(d=base, scale_units=("02a",))),
         ("02a, 03a, 04a scales free", dict(d=base, scale_units=("02a", "03a", "04a"))),
         ("fs free per band", dict(d=base, fs_free=True)),
         ("01a + NEOWISE only", dict(d=L.nightly(RAW, units=["01a"]))),
         ("02a + NEOWISE only", dict(d=L.nightly(RAW, units=["02a"]))),
         ("chi_n < 100 epochs only", dict(d=L.nightly(RAW, chi_max=100))),
         ("frac floor 2%", dict(d=L.nightly(RAW, frac=0.02))),
         ("window 57900-58200 only", dict(d=L.nightly(RAW, window=(57900, 58200)))),
         ("window 57400-58700", dict(d=L.nightly(RAW, window=(57400, 58700)))),
         ("drop Jul 30 + Aug 5 (first two nights)", dict(d=base[~base.mjd.between(57960, 57975)])),
         ("drop all o nights after Dec 1 2017", dict(d=base[~(base.mjd.between(58088, 58300))])),
         ("drop 58055-58077 (late fall wing)", dict(d=base[~base.mjd.between(58050, 58080)])),
         ("event only: 57950-58090 + baseline", dict(d=base[(base.mjd.between(57950, 58090)) | (base.mjd < 57900) | (base.mjd > 58200)])),
         ]
    for tag, kw in V:
        d = kw.pop("d")
        r, _, _ = summarise(tag, d, **kw)
        rows.append(r)
        print(tag, "|", {k: r[k] for k in ("N", "chi2_static", "chi2_par", "dchi2", "piE_N", "piE_E", "piE", "tE", "u0", "Amax")})
    for r in rows:
        if "piE_N" in r and r["piE_N"] == r["piE_N"]:
            r["pi_par"] = round(r["piE_N"] * A_HAT[0] + r["piE_E"] * A_HAT[1], 3); r["pi_perp"] = round(-r["piE_N"] * A_HAT[1] + r["piE_E"] * A_HAT[0], 3)
    T = pd.DataFrame(rows)
    T.to_csv(OUT + "r4_variants.csv", index=False)
    print(T.to_string())
    if "--jack" in sys.argv:
        J = []
        nights = base[base.band.isin(["c", "o", "W1"])].mjd.round(0).unique()
        evn = [m for m in nights if 57950 < m < 58200] + [57993.0]
        for m in evn:
            if m == 57993.0:
                d = base[~base.band.isin(["W1", "W2"])]; tag = "NEOWISE"
            else:
                d = base[~((base.mjd.round(0) == m) & base.band.isin(["c", "o"]))]; tag = f"{m:.0f}"
            st = [[58011, 47, u0] + pi for u0 in (0.14, -0.14) for pi in ([-1, -0.4], [0.5, 0.3], [-0.3, -0.3])]
            r = fit(d, "par", starts=st); s = fit(d, "static")
            J.append(dict(dropped=tag, chi2_par=r["chi2"], dchi2=s["chi2"] - r["chi2"], piE_N=r["p"][3], piE_E=r["p"][4], piE=np.hypot(*r["p"][3:5]), u0=r["p"][2], tE=r["p"][1]))
        J = pd.DataFrame(J).round(3)
        J.to_csv(OUT + "r4_jackknife.csv", index=False)
        print(J.to_string())
    if "--grid" in sys.argv:
        G = []
        for piN in np.arange(-2.5, 2.51, 0.1):
            for piE in np.arange(-1.5, 1.51, 0.1):
                for sgn in (1, -1):
                    st = [[58011, 47, sgn * u0] for u0 in (0.08, 0.15, 0.3)]
                    r = fit(base, "par", fixed=(piN, piE), starts=st, u0sign=sgn)
                    G.append(dict(piE_N=piN, piE_E=piE, sgn=sgn, chi2=r["chi2"], u0=r["p"][2], tE=r["p"][1], t0=r["p"][0]))
        G = pd.DataFrame(G)
        G.to_csv(OUT + "r4_grid.csv", index=False)
        print(G.sort_values("chi2").head(15).to_string())
