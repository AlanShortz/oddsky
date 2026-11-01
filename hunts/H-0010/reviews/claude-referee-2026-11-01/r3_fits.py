"""r3: refits of the five best candidates (and, with --all, every one of the 21) on the r1 Gaia DR3 epoch photometry, with
fitlib (own code). Per star:
  * event transits: G, BP, RP flux ratios with errors (formal + baseline excess scatter), no BP/RP clipping against G;
  * the colour test: per event transit (G >= 5 sigma above baseline) Delta(BP-RP) with its error, weighted mean and chi2 against
    zero; and the excess-flux ratio k = (F_BP-1)/(F_RP-1) by weighted total least squares through the origin, with a bootstrap
    over event transits;
  * point lens, static and parallax, with fs <= 1 in every band (physical: no negative blend), and the investigators' fs <= 1.5;
  * shapes: Gaussian, asymmetric Gaussian, Pearson VII (sym/asym), FRED with free per-band amplitudes; BIC table;
  * NEOWISE: the measured visit ratios (r5) against each model's prediction (G-band model, fs_G as fitted; the WISE beam can only
    dilute more), and a joint fit with W1/W2 as extra series (own fs <= 1) where NEOWISE has a visit in the event.
Run: uv run python -I hunts/H-0010/reviews/claude-referee-2026-11-01/r3_fits.py [--all]"""
import json, os, sys, warnings
import numpy as np, pandas as pd
from astropy.time import Time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fitlib import Lens, bic, load_gaia, shape  # noqa: E402

warnings.filterwarnings("ignore")
C = pd.read_csv(os.path.join(HERE, "data", "candidates21.csv"), dtype={"source_id": str}).set_index("source_id")
NWR = pd.read_csv(os.path.join(HERE, "data", "neowise_ratios.csv"), dtype={"source_id": str})
# event windows (baseline = outside); the five best by hand from the light curves, the others from the investigators' episode bounds
WIN = {"4067152339419332992": (57000, 57200), "5958944416543307648": (56800, 57200), "5893807634053861120": (56940, 57190),
       "5620272814897694848": (56900, 57300), "2054828730840779520": (57250, 57470)}
# NEOWISE visit ratios to use as data (r5): J174618 uses the AllWISE-baseline range (see r5/r5b), not the survey visit baseline
J174618_W = [(57100.0, 8.3, 1.5, "W1"), (57100.0, 9.5, 1.7, "W2")]
date = lambda m: Time(m, format="mjd").iso[:10]


def colour(df):
    g = df[df.g == "G"].set_index("tid")
    hot = g[((g.f - 1) / g.e > 5) & (g.f > 1.05)]
    rows = []
    for tid, r in hot.iterrows():
        bp, rp = df[(df.g == "BP") & (df.tid == tid)], df[(df.g == "RP") & (df.tid == tid)]
        if len(bp) and len(rp):
            rows.append((r.t, r.f, bp.f.iloc[0], bp.e.iloc[0], rp.f.iloc[0], rp.e.iloc[0]))
    if not rows:
        return None
    c = pd.DataFrame(rows, columns=["t", "fG", "fBP", "eBP", "fRP", "eRP"])
    dc = -2.5 * np.log10(c.fBP / c.fRP)
    ec = 1.0857 * np.hypot(c.eBP / c.fBP, c.eRP / c.fRP)
    w = 1 / ec ** 2
    mean, emean = float((w * dc).sum() / w.sum()), float(1 / np.sqrt(w.sum()))
    chi0 = float(((dc / ec) ** 2).sum())

    def kfit(cc):
        x, y = cc.fRP - 1, cc.fBP - 1
        k = float((x * y).sum() / (x * x).sum())
        for _ in range(5):
            w2 = 1 / (cc.eBP ** 2 + (k * cc.eRP) ** 2)
            k = float((w2 * x * y).sum() / (w2 * x * x).sum())
        return k, float(1 / np.sqrt((w2 * x * x).sum()))
    k, ek = kfit(c)
    rng = np.random.default_rng(1)
    bs = [kfit(c.iloc[rng.integers(0, len(c), len(c))])[0] for _ in range(300)] if len(c) >= 3 else [np.nan]
    return dict(n=len(c), dcol=mean, dcol_err=emean, chi2_zero=chi0, k=k, k_err=ek, k_boot16=np.nanpercentile(bs, 16),
                k_boot84=np.nanpercentile(bs, 84), rows=c.assign(dcol=dc, ecol=ec))


def run(sid, win, full=True):
    c = C.loc[sid]
    df, base, dropped = load_gaia(os.path.join(HERE, "data", "epoch_raw", f"{sid}.csv"), win)
    print(f"\n######## {c['name']} ({sid}) window {date(win[0])}..{date(win[1])}")
    print(" baselines:", json.dumps(base))
    if dropped:
        print(" dropped as gross (>3 mag) BP/RP outliers:", dropped)
    ev = df[(df.t > win[0]) & (df.t < win[1])].sort_values(["t", "g"])
    piv = ev.pivot_table(index=["tid"], columns="g", values=["f", "e"], aggfunc="first")
    tt = ev.groupby("tid").t.min()
    print(" event-window transits (flux ratio +- error):")
    for tid in tt.sort_values().index:
        s = "  ".join(f"{b} {piv.loc[tid, ('f', b)]:.3f}+-{piv.loc[tid, ('e', b)]:.3f}" for b in ("G", "BP", "RP") if ('f', b) in piv.columns and np.isfinite(piv.loc[tid, ('f', b)]))
        print(f"   {tt[tid]:.2f} {date(tt[tid])}  {s}")
    col = colour(df)
    if col:
        print(f" colour at {col['n']} transits with G >= 5 sigma: <Delta(BP-RP)> {col['dcol']:+.3f} +- {col['dcol_err']:.3f} (chi2 vs 0: {col['chi2_zero']:.1f} "
              f"for {col['n']}); k = {col['k']:.3f} +- {col['k_err']:.3f} (bootstrap 16-84%: {col['k_boot16']:.2f}-{col['k_boot84']:.2f})")
        for r in col["rows"].itertuples():
            print(f"     {date(r.t)} G x{r.fG:.2f} BP x{r.fBP:.2f}+-{r.eBP:.2f} RP x{r.fRP:.2f}+-{r.eRP:.2f} Delta(BP-RP) {r.dcol:+.3f}+-{r.ecol:.3f}")
    res = {"source_id": sid, "name": c["name"], "colour_n": col["n"] if col else 0, "k": col["k"] if col else np.nan,
           "k_err": col["k_err"] if col else np.nan, "dcol": col["dcol"] if col else np.nan, "dcol_err": col["dcol_err"] if col else np.nan,
           "dcol_chi2": col["chi2_zero"] if col else np.nan}
    fit_df = df[["t", "f", "e", "g"]]
    extra = None
    nw = NWR[NWR.source_id == sid]
    if sid == "4067152339419332992":
        extra = pd.DataFrame([dict(t=t, f=f, e=e, g=g) for t, f, e, g in J174618_W])
    elif len(nw):
        rows = []
        for r in nw.itertuples():
            e1 = max(r.rms1, 0.03) * 0.921 * r.W1
            rows += [dict(t=r.mjd, f=r.W1, e=e1, g="W1"), dict(t=r.mjd, f=r.W2, e=max(e1, 0.05 * r.W2), g="W2")]
        extra = pd.DataFrame(rows)
    tpk = float(df[df.g == "G"].t.values[np.argmax(df[df.g == "G"].f.values)])
    n = len(fit_df)
    models = {}
    variants = [("static fs<=1", False, 1.0), ("parallax fs<=1", True, 1.0), ("static fs<=1.5", False, 1.5)] if full else [("static fs<=1", False, 1.0)]
    for lab, par, fsm in variants:
        L = Lens(fit_df, c.ra, c.dec, parallax=par, fs_max=fsm, t0par=tpk)
        p, chi2 = L.fit(tpk)
        k = len(p)
        fsd = dict(zip(L.free_fs, np.round(p[L.nl:], 3)))
        pred = ""
        if extra is not None:
            ts = np.unique(extra.t.values)
            dn = de = None
            if par:
                from oddsky.analysis.lensing import sun_offsets
                dn, de = sun_offsets(ts, c.ra, c.dec, L.t0par)
            pr = L.model(p, t=ts, dn=dn, de=de, which="G")
            src = (pr - 1 + fsd["G"]) / fsd["G"]
            pred = "; predicted at NEOWISE " + ", ".join(f"{date(t)} G-model x{a:.2f} (source x{s:.2f})" for t, a, s in zip(ts, pr, src))
        models[lab] = dict(chi2=chi2, k=k, bic=bic(chi2, k, n), p=p)
        print(f" {lab:16s} chi2 {chi2:8.1f} (n {n}, k {k}) BIC {bic(chi2, k, n):8.1f} t0 {date(p[0])} tE {p[1]:6.1f} u0 {p[2]:+.3f}"
              + (f" piE ({p[3]:+.2f},{p[4]:+.2f})" if par else "") + f" fs {fsd}{pred}")
        res[f"{lab}_chi2"], res[f"{lab}_tE"], res[f"{lab}_u0"], res[f"{lab}_t0"], res[f"{lab}_fs"] = chi2, p[1], p[2], p[0], json.dumps({k: float(v) for k, v in fsd.items()})
    for kind in ("gauss", "gauss_asym", "pv7", "pv7_asym", "fred"):
        chi2, x, _ = shape(fit_df, kind, tpk)
        k = len(x)
        models[kind] = dict(chi2=chi2, k=k, bic=bic(chi2, k, n))
        print(f" {kind:16s} chi2 {chi2:8.1f} (k {k}) BIC {bic(chi2, k, n):8.1f}  params {np.round(x, 2).tolist()}")
        res[f"{kind}_chi2"] = chi2
    bl = min(models[m]["bic"] for m in models if m.startswith(("static fs<=1", "parallax fs<=1")) and "1.5" not in m)
    bs = min(models[m]["bic"] for m in ("gauss", "gauss_asym", "pv7", "pv7_asym", "fred"))
    res["dbic_shape_minus_lens_fs1"] = bs - bl
    print(f" => best shape BIC minus best physical lens BIC (fs<=1): {bs - bl:+.1f}  (positive favours the lens)")
    if extra is not None and full:
        J = pd.concat([fit_df, extra], ignore_index=True)
        for lab, par in (("joint static fs<=1", False), ("joint parallax fs<=1", True)):
            L = Lens(J, c.ra, c.dec, parallax=par, fs_max=1.0, t0par=tpk)
            p, chi2 = L.fit(tpk)
            fsd = dict(zip(L.free_fs, np.round(p[L.nl:], 3)))
            r_w = (L.model(p) - L.f) / L.e
            wres = "; ".join(f"{g} {date(t)} obs x{f:.2f} model x{m:.2f}" for g, t, f, m in zip(J.g, J.t, J.f, L.model(p)) if g.startswith("W"))
            print(f" {lab:20s} chi2 {chi2:8.1f} (n {len(J)}) t0 {date(p[0])} tE {p[1]:6.1f} u0 {p[2]:+.3f} fs {fsd} | {wres}")
            res[f"{lab}_chi2"], res[f"{lab}_tE"], res[f"{lab}_fs"] = chi2, p[1], json.dumps({k: float(v) for k, v in fsd.items()})
        for kind in ("pv7", "pv7_asym", "fred"):
            chi2, x, _ = shape(J, kind, tpk)
            print(f" joint {kind:14s} chi2 {chi2:8.1f} (k {len(x)})")
            res[f"joint {kind}_chi2"] = chi2
    return res


if __name__ == "__main__":
    out = []
    ids = list(WIN)
    if "--all" in sys.argv:
        inv = pd.read_csv(os.path.join(HERE, "..", "..", "work", "gaia_ml_unpub.csv"), dtype={"source_id": str}).set_index("source_id")
        for sid in C.index:
            if sid in WIN:
                continue
            r = inv.loc[sid]
            a, b = float(r.ep_first), float(r.ep_last)
            WIN[sid] = (a - max(60, 1.0 * (b - a)) - 30, b + max(60, 1.0 * (b - a)) + 30)
        ids = list(C.index)
    for sid in ids:
        out.append(run(sid, WIN[sid], full=sid in list(WIN)[:5] or "--full" in sys.argv))
    pd.DataFrame(out).to_csv(os.path.join(HERE, "data", "r3_fits" + ("_all" if "--all" in sys.argv else "") + ".csv"), index=False)
