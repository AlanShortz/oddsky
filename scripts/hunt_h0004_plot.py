"""Hunt H-0004: one PNG per star so a human (or a referee agent) can look before anyone believes a verdict.

  .venv/bin/python scripts/hunt_h0004_plot.py T20-5021 T20-2157 ...
  .venv/bin/python scripts/hunt_h0004_plot.py --verdicts rcb_like,eclipse_like     # from scored.csv

Writes hunts/H-0004/plots/<id>.png: all bands on one time axis, nightly medians, upper limits as triangles,
the deepest detected fade shaded, and the feature summary in the title.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from oddsky.analysis import fades  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from hunt_h0004_fetch import load_star  # noqa: E402

here = Path("hunts/H-0004")
lc_dir = here / "lc"
out_dir = here / "plots"
COLOURS = {"ATLAS_o": "orangered", "ATLAS_c": "teal", "ZTF_g": "green", "ZTF_r": "crimson", "ZTF_i": "saddlebrown"}


def plot(cid: str, meta: pd.Series | None = None) -> Path | None:
    df, _ = load_star(cid)
    if df.empty:
        return None
    f = fades.rcb_features(df)
    verdict = fades.classify_fade(f)
    fig, ax = plt.subplots(figsize=(13, 5))
    for band in sorted(df.band.unique()):
        c = COLOURS.get(band, "gray")
        g = df[(df.band == band) & (df.flag == "")]
        ax.errorbar(g.t_mjd, g.mag, g.err, fmt=".", ms=3, color=c, alpha=0.45, lw=0.4, label=f"{band} ({len(g)})")
        lim = df[(df.band == band) & (df.flag == "upper_limit")]
        if len(lim):
            ax.plot(lim.t_mjd, lim.mag, "v", ms=3, color=c, alpha=0.25)
    if f.get("band"):
        n = fades.nightly(df, f["band"])
        n = n[~n.lim]
        ax.plot(n.t_mjd, n.mag, "k-", lw=0.8, alpha=0.6, label=f"nightly {f['band']}")
        ax.axhline(f["bright"], color="k", ls=":", lw=0.8)
        for ev in f.get("events", [])[:3]:
            ax.axvspan(ev["start_mjd"], ev["end_mjd"], color="gold", alpha=0.15)
    ax.invert_yaxis()
    ax.set_xlabel("MJD")
    ax.set_ylabel("mag")
    name = ""
    if meta is not None:
        bits = [str(meta.get("wise_id") or ""), str(meta.get("simbad_main_id") or ""), str(meta.get("simbad_otype") or "")]
        name = " ".join(b for b in bits if b and b != "nan")
    title = (f"{cid} {name}  |  {verdict}  depth {f.get('depth', 0) or 0:.2f}  rate {f.get('decline_rate_mag_per_day', 0) or 0:.3f}/d  "
             f"asym {f.get('asymmetry') if f.get('asymmetry') is None else round(f['asymmetry'], 2)}"
             f"{'(lb)' if f.get('asymmetry_is_lower_bound') else ''}  LS {f.get('ls_power', 0) or 0:.2f}@{f.get('ls_period', 0) or 0:.0f}d  "
             f"fold {f.get('fold_power', 0) or 0:.2f}  max_frac {f.get('max_frac', 0) or 0:.2f}")
    ax.set_title(title, fontsize=9)
    ax.legend(fontsize=7, ncol=6, loc="lower left")
    # a calendar axis on top
    top = ax.secondary_xaxis("top", functions=(lambda m: 2000 + (m - 51544.5) / 365.25, lambda y: 51544.5 + (y - 2000) * 365.25))
    top.set_xlabel("year")
    fig.tight_layout()
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"{cid}.png"
    fig.savefig(out, dpi=110)
    plt.close(fig)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--verdicts", default=None)
    ap.add_argument("--scored", default="scored.csv")
    a = ap.parse_args()
    cand = pd.read_csv(here / "candidates.csv").set_index("id")
    ids = list(a.ids)
    if a.verdicts:
        sc = pd.read_csv(here / a.scored)
        ids += [i for i in sc[sc.verdict.isin(a.verdicts.split(","))].id if i not in ids]
    for cid in ids:
        out = plot(cid, cand.loc[cid] if cid in cand.index else None)
        print(cid, out or "no data", flush=True)


if __name__ == "__main__":
    main()
