"""r17: windowed fits (|t - t0| < 3 tE, the investigators' style) with oddsky Problem, with and without the ZTF catflags=32768
nights, the asymmetry test in the window, and a four-panel figure of data + best static-blend model."""
import json, os, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from targets import TARGETS
from r4_fits import series_for, asym
from oddsky.analysis.lensing import Problem, magnification
res = {}
fig, axs = plt.subplots(5, 1, figsize=(10, 20))
for ax, k in zip(axs, ["J204610", "J190512", "J173342", "J180624", "J180441"]):
    name, ra, dec, t, pix = TARGETS[k]
    for cat0 in (True, False):
        df = series_for(k, cat0=cat0)
        p0 = Problem(df.t.values, df.f.values, df.e.values, df.g.values, blend=False)
        b0, _ = p0.fit(t0c=float(df.t[df.f.idxmax()]))
        w = df[(df.t - b0[0]).abs() < 3 * b0[1]]
        out = {}
        for lab, kw in (("static", dict(blend=False)), ("static_blend", dict(blend=True)), ("parallax_blend", dict(blend=True, parallax=True, ra=ra, dec=dec))):
            p = Problem(w.t.values, w.f.values, w.e.values, w.g.values, **kw)
            b, chi2 = p.fit(t0c=b0[0])
            out[lab] = {"chi2": round(chi2, 1), "n": len(w), "k": len(b), "t0": round(b[0], 2), "tE": round(b[1], 1), "u0": round(b[2], 3), "Amax": round(float(magnification(b[2])), 2)}
            if kw.get("parallax"):
                out[lab]["piE"] = [round(b[3], 2), round(b[4], 2)]
            if kw.get("blend"):
                out[lab]["fs"] = {g: round(float(v), 2) for g, v in zip(p.names, b[p.nlens:])}
            if lab == "static_blend" and cat0:
                best, prob, wfit = b, p, w
        out["asym"] = asym(w, out["static"]["t0"], out["static"]["tE"], out["static"]["u0"])
        res[f"{k}_{'cat0' if cat0 else 'allflags'}"] = out
        print(k, "catflags=0" if cat0 else "all flags", json.dumps(out), flush=True)
    w = wfit
    tt = np.linspace(w.t.min(), w.t.max(), 2000)
    for g, d in w.groupby("g"):
        fs = best[prob.nlens + prob.names.index(g)]
        ax.errorbar(d.t, (d.f - 1) / fs + 1, d.e / fs, fmt="o", ms=3, label=g)
    ax.plot(tt, magnification(np.hypot((tt - best[0]) / best[1], best[2])), "k-", lw=1)
    ax.set_title(f"{name}: static point lens + blend, t0 {best[0]:.1f}, tE {best[1]:.1f} d, u0 {best[2]:.3f} (deblended)")
    ax.set_ylabel("magnification"); ax.legend(fontsize=7)
plt.tight_layout(); plt.savefig(f"{HERE}/r17_fits.png", dpi=80)
json.dump(res, open(f"{HERE}/r17_window.json", "w"), indent=1)
