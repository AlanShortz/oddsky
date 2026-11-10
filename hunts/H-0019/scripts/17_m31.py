"""M31, added after the registered run (exploratory). The 189 fields Hubble revisited more than 100 d apart (from the
MAST observation list) were fetched as tiles; the registered measurement code is applied unchanged, then the result's
dependence on where the tip is put, on lag and on distance from the centre is tabulated. Writes work/m31.json and
work/pairs/MESSIER031.parquet (ignored by git). M31 is NOT added to work/measure.csv or the registered tests."""
import json, pathlib
import numpy as np, pandas as pd

HERE = pathlib.Path(__file__).resolve().parents[1]
src = (HERE / "scripts/04_measure.py").read_text().split('if __name__ == "__main__":')[0]
ns = {"__file__": str(HERE / "scripts/04_measure.py")}; exec(compile(src, "04_measure.py", "exec"), ns)
g = [r for r in ns["probe_rows"]() if r["name"] == "MESSIER031"][0]; g["AB"] = 0.27; g["key"] = "MESSIER031"   # A_B from Karachentsev+2013
row, p = ns["measure"](g)
L = p[p.kind == "long"].copy(); S = p[p.kind == "short"]
tip_used = row["tip"]; mag_rel = L.rel + tip_used


def E(s, x=0.3):
    a, r = s[s.box == "agb"], s[s.box == "rgb"]
    f1, f2 = (a.d.abs() > x).mean(), (r.d.abs() > x).mean()
    return dict(E=round(float(f1 - f2), 4), se=round(float(np.sqrt(f1 * (1 - f1) / len(a) + f2 * (1 - f2) / len(r))), 4), n_agb=len(a), n_rgb=len(r), f_agb=round(float(f1), 4), f_rgb=round(float(f2), 4))


out = dict(registered={k: (v if not isinstance(v, float) else round(v, 4)) for k, v in row.items() if not k.startswith(("k02", "k05"))}, E03=E(L), E02=E(L, 0.2), E05=E(L, 0.5),
           short=dict(f03_agb=round(float((S[S.box == "agb"].d.abs() > 0.3).mean()), 5), n_agb=int((S.box == "agb").sum()), f03_rgb=round(float((S[S.box == "rgb"].d.abs() > 0.3).mean()), 5)),
           n_image_pairs=int(L.groupby(["img1", "img2"]).ngroups), dimmed_vs_brightened=[int(((L.box == "agb") & (L.d > 0.3)).sum()), int(((L.box == "agb") & (L.d < -0.3)).sum())])
out["by_tip"] = {}
for tip in (row["tip_pred"], 21.3, 21.4, 21.5, tip_used):
    s = L[L.cls == "red"].copy(); rel = mag_rel[s.index] - tip
    s["box"] = np.select([(rel >= -1) & (rel < 0), (rel > 0) & (rel <= 0.5)], ["agb", "rgb"], "other")
    out["by_tip"][f"{tip:.2f}"] = E(s)
out["by_lag"] = {f"{lo}-{hi}": E(L[(L.lag >= lo) & (L.lag < hi)]) for lo, hi in [(100, 250), (250, 700), (700, 2000), (2000, 6000)] if ((L.lag >= lo) & (L.lag < hi) & (L.box == "agb")).sum() > 200}
cd = np.cos(np.radians(41.27)); L["r"] = np.hypot((L.MatchRA - 10.6847) * cd, L.MatchDec - 41.2687)
out["by_radius_deg"] = {f"{lo}-{hi}": E(L[(L.r >= lo) & (L.r < hi)]) for lo, hi in [(0, 0.25), (0.25, 0.6), (0.6, 1.0), (1.0, 2.0)] if ((L.r >= lo) & (L.r < hi) & (L.box == "agb")).sum() > 200}
q = L[L.cls == "red"].col.quantile([1 / 3, 2 / 3]).values
out["by_colour_third"] = {n: E(L[(L.col >= lo) & (L.col < hi)]) for n, lo, hi in (("bluest", -9, q[0]), ("middle", q[0], q[1]), ("reddest", q[1], 99))}
ip = pd.DataFrame([E(s) for _, s in L[L.box.isin(["agb", "rgb"])].groupby(["img1", "img2"]) if (s.box == "agb").sum() >= 150 and (s.box == "rgb").sum() >= 150])
if len(ip):
    w = 1 / ip.se ** 2; m = (w * ip.E).sum() / w.sum()
    out["image_pairs"] = dict(n=len(ip), weighted_mean=round(float(m), 4), chi2=round(float((w * (ip.E - m) ** 2).sum()), 1), min=round(float(ip.E.min()), 4), max=round(float(ip.E.max()), 4),
                              scatter=round(float(ip.E.std()), 4))
(HERE / "work/m31.json").write_text(json.dumps(out, indent=1, default=float))
for k, v in out.items():
    print(k, json.dumps(v, default=float)[:520])
