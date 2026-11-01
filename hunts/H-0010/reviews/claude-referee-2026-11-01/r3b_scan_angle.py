"""r3b: scan-angle test for all 21 candidates. Each Gaia DR3 G transit is matched (within 60 s) to the GOST prediction for the
position, which gives the field of view (FOV1 preceding / FOV2 following) and the scan angle. A blended pair measured differently
along different scan directions (the investigators' impostor class) brightens whenever the scan angle (mod 180 deg) returns to the
same value, so: (i) the event transits' scan angles; (ii) baseline transits (outside the event window) with scan angle within
+-20 deg (mod 180) of an event transit: their flux ratios; (iii) a robust correlation of baseline G residual with scan angle
(binned in 30-deg bins); (iv) same-day FOV1/FOV2 pairs during the event (an artifact need not repeat in both FoVs 106 min apart).
Run: uv run python -I hunts/H-0010/reviews/claude-referee-2026-11-01/r3b_scan_angle.py"""
import os, sys
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fitlib import load_gaia  # noqa: E402
from r3_fits import WIN  # noqa: E402  (five best)

C = pd.read_csv(os.path.join(HERE, "data", "candidates21.csv"), dtype={"source_id": str}).set_index("source_id")
inv = pd.read_csv(os.path.join(HERE, "..", "..", "work", "gaia_ml_unpub.csv"), dtype={"source_id": str}).set_index("source_id")
rows = []
for sid in C.index:
    if sid in WIN:
        win = WIN[sid]
    else:
        a, b = float(inv.loc[sid, "ep_first"]), float(inv.loc[sid, "ep_last"])
        win = (a - max(60, b - a) - 30, b + max(60, b - a) + 30)
    df, base, _ = load_gaia(os.path.join(HERE, "data", "epoch_raw", f"{sid}.csv"), win, band_list=("G",))
    g = pd.read_csv(os.path.join(HERE, "data", f"gost_{sid}.csv"))
    tg = df.t.values - 55197.0
    j = np.array([np.argmin(np.abs(g.t_gaia.values - x)) for x in tg])
    dt = np.abs(g.t_gaia.values[j] - tg) * 86400
    df["fov"] = np.where(dt < 60, g.fov.values[j], "?")
    df["ang"] = np.where(dt < 60, np.degrees(g.scan_angle.values[j]) % 180, np.nan)
    inside = (df.t > win[0]) & (df.t < win[1])
    sig = (df.f - 1) / df.e
    evt = df[inside & (sig > 5) & (df.f > 1.05)]
    bl = df[~inside]
    print(f"\n{C.loc[sid, 'name']}: {len(df)} G transits, {int((dt < 60).sum())} matched to GOST; baseline scatter {base['G']['scatter']:.4f}")
    worst = 0.0
    for r in evt.itertuples():
        d = np.abs(((bl.ang - r.ang) + 90) % 180 - 90)
        sim = bl[d < 20]
        mx = (sim.f - 1).max() if len(sim) else np.nan
        worst = max(worst, (sim.f.max() - 1) / max(r.f - 1, 1e-3)) if len(sim) else worst
        print(f"   event {r.t:.2f} {r.fov} angle {r.ang:5.1f}: G x{r.f:.3f}; baseline transits within 20 deg: {len(sim)}, "
              f"max excess {mx:+.3f}, median {np.median(sim.f - 1) if len(sim) else np.nan:+.4f}")
    # baseline residual vs angle
    bins = pd.cut(bl.ang, np.arange(0, 181, 30))
    st = bl.groupby(bins, observed=True).f.agg(["median", "size"])
    spread = float(st["median"].max() - st["median"].min()) if len(st) > 1 else np.nan
    # FOV pairs within the event
    pairs = []
    e2 = df[inside].sort_values("t")
    for i in range(len(e2) - 1):
        a, b = e2.iloc[i], e2.iloc[i + 1]
        if b.t - a.t < 0.1 and a.fov != b.fov and max(a.f, b.f) > 1.1:
            pairs.append(f"{a.fov} x{a.f:.3f} / {b.fov} x{b.f:.3f} ({(a.f - b.f) / np.hypot(a.e, b.e):+.1f} sig)")
    print(f"   baseline median flux ratio by 30-deg scan-angle bin: {st['median'].round(4).tolist()} (n {st['size'].tolist()}); spread {spread:.4f}")
    print(f"   same-day FOV pairs in the event: {'; '.join(pairs) if pairs else 'none'}")
    print(f"   distinct event dates: {len(np.unique(np.round(evt.t)))}; event scan angles: {sorted(np.round(evt.ang).tolist())}")
    rows.append(dict(source_id=sid, name=C.loc[sid, "name"], n_event=len(evt), n_dates=len(np.unique(np.round(evt.t))),
                     angles=";".join(str(int(a)) for a in sorted(evt.ang.dropna().round())), worst_baseline_frac=worst, angle_spread=spread,
                     pairs=" | ".join(pairs)))
pd.DataFrame(rows).to_csv(os.path.join(HERE, "data", "r3b_scan_angle.csv"), index=False)
