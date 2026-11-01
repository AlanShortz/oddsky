"""a7: the a5/a6 frame residuals again, with the quiet comparison frames restricted to the same PSF era as the event (02a before
2017-01-01, maj ~3.4-6 px; 01a before 2020-01-01, maj ~3-4 px) and |dt| > 150 d. This removes any dependence on later reductions
or on the narrow-PSF years, at the price of fewer comparison frames. Night-pooled excess per band within +-60 d (all event frames with
kNN distance < 1.0 px), and the night-by-night values.
Run: uv run python -I hunts/H-0010/reviews/atlas-2026-11-01/a7_era.py"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, KEYS, atlas_raw, clean, mjd2date, targets  # noqa: E402

pd.set_option("display.width", 250)
T = targets()
SH = json.load(open(os.path.join(DATA, "a1_shares.json")))
ERA_END = {"02a": 57754.0, "01a": 58849.0}
KF = 25
EXTRA = {"J184922": (57660, 57700)}


def feats(d):
    e = d.maj - d["min"]
    return np.vstack([d.maj, d["min"], e * np.cos(2 * np.radians(d.phi)), e * np.sin(2 * np.radians(d.phi))]).T


OUT = {}
for k in KEYS:
    t = T[k]
    t0 = t["t0"]
    r = clean(atlas_raw(k))
    r["dt"] = r.mjd - t0
    win = np.abs(r.dt) <= 60
    if k in EXTRA:
        win |= (r.mjd >= EXTRA[k][0]) & (r.mjd <= EXTRA[k][1])
    ev = r[win]
    if len(ev) == 0:
        continue
    print("=" * 30, k, t["name"])
    rows = []
    for (F, cam), e in ev.groupby(["F", "cam"]):
        q = r[(r.F == F) & (r.cam == cam) & (np.abs(r.dt) > 150) & (r.mjd < ERA_END.get(cam, 99999))]
        if len(q) < KF + 5:
            print(f"  {F} {cam}: only {len(q)} same-era quiet frames; skipped")
            continue
        Xq, Xe = feats(q), feats(e)
        for j, row in enumerate(e.itertuples()):
            dd = np.sqrt(np.sum((Xq - Xe[j]) ** 2, axis=1))
            o = np.argsort(dd)[:KF]
            v = q.ujy.values[o]
            med = np.median(v)
            sc = 1.4826 * np.median(np.abs(v - med))
            rows.append(dict(date=mjd2date(row.mjd), dt=row.dt, F=F, cam=cam, resid=row.ujy - med, err=np.hypot(sc, row.dujy),
                             kd=dd[o].max()))
        print(f"  {F} {cam}: {len(q)} same-era quiet frames")
    R = pd.DataFrame(rows)
    R = R[R.kd < 1.0]
    nb = R.groupby(["date", "F", "cam"]).apply(lambda x: pd.Series(dict(
        dt=x.dt.mean(), n=len(x), exc=np.average(x.resid, weights=1 / x.err**2),
        err=max(1 / np.sqrt(np.sum(1 / x.err**2)), x.resid.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else 0))), include_groups=False).reset_index()
    nb["sig"] = nb.exc / nb.err
    print(nb.round(1).to_string(index=False))
    s = {}
    for F in ("o", "c"):
        d = nb[nb.F == F]
        if len(d) == 0:
            continue
        w = 1 / d.err**2
        m, me = float(np.sum(w * d.exc) / np.sum(w)), float(1 / np.sqrt(np.sum(w)))
        Fb = SH[k]["fc_star" if F == "c" else "fo_star"]
        s[F] = dict(nights=len(d), exc=m, err=me)
        print(f"  {F}: {len(d)} nights, pooled excess {m:+.1f} +- {me:.1f} uJy ({m / Fb:+.2f} +- {me / Fb:.2f} of the Gaia star's {F} flux)")
    OUT[k] = s
json.dump(OUT, open(os.path.join(DATA, "a7_summary.json"), "w"), indent=1, default=float)
