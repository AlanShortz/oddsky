"""a6: are the odd event-night frames tied to a detector position? For every unit/band series, quiet frames (|dt| > 150 d) get the
same leave-one-out kNN PSF residual as in a5; residuals are binned by detector position (1500-px cells). For each event frame (a5) the
quiet frames of the same unit within 600 px of its detector position give a local residual median and scatter; the event frame is
then re-judged against them ('local z'). Then the frame-level event test with only well-matched frames (kNN PSF distance < 1.0 px):
weighted mean residual per band within +-30 / +-90 d, and the same against the Gaia prediction (a4's fs = 1 lens on the Gaia star).
Run: uv run python -I hunts/H-0010/reviews/atlas-2026-11-01/a6_position.py"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, KEYS, atlas_raw, clean, mjd2date, targets  # noqa: E402

from oddsky.analysis.lensing import magnification  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 300)
T = targets()
SH = json.load(open(os.path.join(DATA, "a1_shares.json")))
A4 = json.load(open(os.path.join(DATA, "a4_summary.json")))
KF = 25
OUT = {}


def feats(d):
    e = d.maj - d["min"]
    return np.vstack([d.maj, d["min"], e * np.cos(2 * np.radians(d.phi)), e * np.sin(2 * np.radians(d.phi))]).T


for k in KEYS:
    t = T[k]
    t0 = t["t0"]
    p = os.path.join(DATA, f"a5_frames_{k}.csv")
    if not os.path.exists(p):
        print("=" * 30, k, "no event frames")
        continue
    E = pd.read_csv(p)
    r = clean(atlas_raw(k))
    r["dt"] = r.mjd - t0
    print("=" * 30, k, t["name"])
    E["loc_med"] = np.nan
    E["loc_sc"] = np.nan
    E["loc_n"] = 0
    for (F, cam), q in r[np.abs(r.dt) > 150].groupby(["F", "cam"]):
        e = E[(E.F == F) & (E.cam == cam)]
        if len(e) == 0:
            continue
        X = feats(q)
        res = np.empty(len(q))
        for i in range(len(q)):
            dd = np.sqrt(np.sum((X - X[i]) ** 2, axis=1))
            dd[i] = np.inf
            o = np.argsort(dd)[:KF]
            res[i] = q.ujy.values[i] - np.median(q.ujy.values[o])
        q = q.assign(res=res)
        q["cell"] = (q.x // 1500).astype(int).astype(str) + "," + (q.y // 1500).astype(int).astype(str)
        g = q.groupby("cell").res.agg(["size", "median"])
        g = g[g["size"] >= 15]
        print(f"  {F} {cam}: quiet-frame kNN residual median by 1500-px detector cell (n >= 15): range {g['median'].min():+.0f} .. "
              f"{g['median'].max():+.0f} uJy over {len(g)} cells; overall robust scatter {1.4826 * np.median(np.abs(res - np.median(res))):.0f}")
        for idx, row in e.iterrows():
            near = q[np.hypot(q.x - row.x, q.y - row.y) < 600]
            if len(near) >= 8:
                m = float(np.median(near.res))
                s = float(1.4826 * np.median(np.abs(near.res - m)))
                E.loc[idx, ["loc_med", "loc_sc", "loc_n"]] = m, s, len(near)
    E["loc_z"] = (E.resid - E.loc_med) / np.hypot(E.loc_sc, E.dujy)
    show = E[(np.abs(E.z) > 1.5) | (np.abs(E.loc_z) > 1.5)]
    if len(show):
        print("  event frames with |z| > 1.5 (kNN) or |local z| > 1.5, with the local (same detector position) quiet residuals:")
        print(show[["date", "dt", "F", "cam", "ujy", "resid", "z", "kdist", "x", "y", "loc_n", "loc_med", "loc_sc", "loc_z"]]
              .round(2).to_string(index=False))
    # frame-level event test, well-matched frames only
    p1 = A4[k]["lens_fs1"]
    Fb = {"c": SH[k]["fc_star"], "o": SH[k]["fo_star"]}
    E["R"] = magnification(np.hypot((E.mjd - p1[0]) / p1[1], p1[2]))
    E["pred"] = E.F.map(Fb) * (E.R - 1)
    E["resid_loc"] = E.resid - E.loc_med.fillna(0)
    E["err"] = np.hypot(E.knn_sc, E.dujy)
    good = E[E.kdist < 1.0]
    summ = {}
    for F in ("o", "c"):
        for win in (30, 60):
            d = good[(good.F == F) & (np.abs(good.dt) <= win)]
            if len(d) == 0:
                continue
            for col in ("resid", "resid_loc"):
                # frames of one night share the night's systematics: pool per night first
                nb = d.groupby("date").apply(lambda x: pd.Series(dict(
                    y=np.average(x[col], weights=1 / x.err**2), e=max(1 / np.sqrt(np.sum(1 / x.err**2)), x[col].std(ddof=1) / np.sqrt(len(x))
                                                                     if len(x) > 1 else 0), pred=x.pred.mean(), n=len(x))), include_groups=False)
                w = 1 / nb.e**2
                m = float(np.sum(w * nb.y) / np.sum(w))
                me = float(1 / np.sqrt(np.sum(w)))
                a = float(np.sum(w * nb.pred * nb.y) / np.sum(w * nb.pred**2)) if np.sum(nb.pred**2) > 0 else np.nan
                ae = float(1 / np.sqrt(np.sum(w * nb.pred**2))) if np.sum(nb.pred**2) > 0 else np.nan
                chi = float(np.sum(w * (nb.y - a * nb.pred) ** 2) / max(len(nb) - 1, 1))
                ae *= np.sqrt(max(chi, 1))
                summ[f"{F}_{win}_{col}"] = dict(nights=len(nb), frames=int(nb.n.sum()), exc=m, err=me, alpha=a, alpha_err=ae,
                                                pred=float(np.mean(nb.pred)))
                print(f"  {F} +-{win} d, kNN distance < 1 px, {col:9s}: {len(nb)} nights / {int(nb.n.sum())} frames; mean excess {m:+.1f} +- "
                      f"{me:.1f} uJy ({m / Fb[F]:+.2f} +- {me / Fb[F]:.2f} of the Gaia star); mean prediction (fs=1 lens) {np.mean(nb.pred):+.1f}; "
                      f"alpha {a:+.2f} +- {ae:.2f}")
    OUT[k] = summ
    E.to_csv(os.path.join(DATA, f"a6_frames_{k}.csv"), index=False)
json.dump(OUT, open(os.path.join(DATA, "a6_summary.json"), "w"), indent=1, default=float)
