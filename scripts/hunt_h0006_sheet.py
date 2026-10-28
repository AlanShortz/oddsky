"""Hunt H-0006, step 3: one diagnostic sheet per survivor of hunt_h0006_vet.py.

Re-extracts NEOWISE from the single-exposure table (independent of the sky pass), adds the AllWISE 2010 point and
the 2MASS 1999 colours, and Gaia DR3 epoch photometry (2014-2017). Writes hunts/H-0006/vet/<designation>_*.csv and
plots/<designation>.png.
"""
from pathlib import Path

import matplotlib
import pandas as pd

from oddsky.data import gaia_epoch, neowise

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

here = Path("hunts/H-0006")


def sheet(r) -> None:
    tag = r.designation
    nw, _ = neowise.lightcurve(r.ra, r.dec)
    nw.to_csv(here / "vet" / f"{tag}_neowise.csv", index=False)
    gl, _ = gaia_epoch.lightcurve(int(r.gaia_source_id))
    gl.to_csv(here / "vet" / f"{tag}_gaia_epoch.csv", index=False)
    fig, ax = plt.subplots(3, 1, figsize=(9, 9), sharex=True)
    w = {b: nw[nw.band == b].set_index("t_mjd") for b in ("W1", "W2")}
    for b, c in (("W1", "#2836d9"), ("W2", "#e0457b")):
        ax[0].errorbar(w[b].index, w[b].mag, w[b].err, fmt="o", ms=4, c=c, label=f"NEOWISE {b}")
    ax[0].plot([55350], [r.w1mpro_allwise], "s", c="#2836d9", mfc="none", label="AllWISE 2010")
    ax[0].plot([55350], [r.w2mpro_allwise], "s", c="#e0457b", mfc="none")
    ax[0].invert_yaxis()
    ax[0].legend(fontsize=7)
    # W1 and W2 visit means carry slightly different times: pair them within a visit (~1 day)
    both = pd.merge_asof(w["W1"][["mag"]].sort_index().rename(columns={"mag": "mag1"}),
                         w["W2"][["mag"]].sort_index().rename(columns={"mag": "mag2"}),
                         left_index=True, right_index=True, direction="nearest", tolerance=3.0).dropna()
    ax[1].plot(both.index, both.mag1 - both.mag2, "o", c="k")
    ax[1].plot([55350], [r.w1mpro_allwise - r.w2mpro_allwise], "s", c="k", mfc="none")
    ax[1].axhline(0.2, ls=":", c="grey")
    ax[1].set_ylabel("W1-W2 (photosphere ~0.1-0.2 for an M star)", fontsize=8)
    if len(gl):
        for b, c in (("G", "k"), ("BP", "#2836d9"), ("RP", "#e0457b")):
            g = gl[gl.band == b] if "band" in gl else gl
            ax[2].plot(g.t_mjd, g.mag, "o", ms=3, c=c, label=f"Gaia {b}")
        ax[2].invert_yaxis()
        ax[2].legend(fontsize=7)
    ax[2].set_xlabel("MJD")
    fig.suptitle(f"{tag}  Gaia DR3 {r.gaia_source_id}  G={r.gaia_g:.2f}  BP-RP={r.gaia_bp_rp:.2f}  M_G={r.abs_g:.2f}", fontsize=9)
    plt.tight_layout()
    plt.savefig(here / "plots" / f"{tag}.png", dpi=90)
    print(tag, "\n", both.assign(c=both.mag1 - both.mag2).round(3).to_string())


def main() -> None:
    v = pd.read_csv(here / "vetted.csv", dtype={"gaia_source_id": str})
    f = pd.read_csv(here / "flags.csv", dtype={"gaia_source_id": str})[["allwise_cntr", "w1mpro_allwise", "w2mpro_allwise"]]
    for r in v[v.survives].merge(f, on="allwise_cntr").itertuples():
        sheet(r)


if __name__ == "__main__":
    main()
