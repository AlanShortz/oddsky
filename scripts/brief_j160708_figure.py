"""Figure for the 30 Oct follow-up note: J160708.51-320101.1's NEOWISE W1/W2 and W1-W2, 2010-2024, with the photospheric
W1-W2 of field M dwarfs of the same colour (0.09 +- 0.04, H-0006 referee). Input: hunts/H-0006/vet/*_neowise.csv (IRSA single
exposures, re-extracted independently of the sky pass). Output: docs/briefs/figures/J160708_followup_2026-10-30.png."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from astropy.time import Time  # noqa: E402

nw = pd.read_csv("hunts/H-0006/vet/J160708.51-320101.1_neowise.csv")
nw = nw[nw.flag.isna() | (nw.flag == "")]
w = {b: nw[nw.band == b].set_index("t_mjd").sort_index() for b in ("W1", "W2")}
both = pd.merge_asof(w["W1"][["mag"]].rename(columns={"mag": "m1"}), w["W2"][["mag"]].rename(columns={"mag": "m2"}),
                     left_index=True, right_index=True, direction="nearest", tolerance=3.0).dropna()
aw = {"W1": 9.856, "W2": 9.426}  # AllWISE 2010 (H-0006 plot)
t_aw = Time(55350, format="mjd").datetime


def dt(x):
    return Time(list(x), format="mjd").datetime


fig, ax = plt.subplots(2, 1, figsize=(7.5, 5.6), sharex=True, gridspec_kw={"height_ratios": [1.2, 1]})
for b, c in (("W1", "#2836d9"), ("W2", "#e0457b")):
    ax[0].errorbar(dt(w[b].index), w[b].mag, w[b].err, fmt="o", ms=4, c=c, label=f"NEOWISE {b}")
    ax[0].plot([t_aw], [aw[b]], "s", c=c, mfc="none", label=f"AllWISE {b}, 2010")
ax[0].invert_yaxis()
ax[0].set_ylabel("magnitude")
ax[0].legend(fontsize=7, ncol=2, loc="lower left")
for a in ax:
    a.axvspan(Time(59432, format="mjd").datetime, Time(59636, format="mjd").datetime, color="0.85", zorder=0)
ax[1].plot(dt(both.index), both.m1 - both.m2, "o", c="k", label="NEOWISE")
ax[1].plot([t_aw], [aw["W1"] - aw["W2"]], "s", c="k", mfc="none", label="AllWISE 2010")
ax[1].axhspan(0.05, 0.13, color="#9bd29b", alpha=0.5, zorder=0, label="field M dwarfs of this colour (photosphere)")
ax[1].set_ylabel("W1 - W2")
ax[1].legend(fontsize=7, loc="lower left", bbox_to_anchor=(0.0, 0.2))
ax[1].text(Time(59400, format="mjd").datetime, 0.2, "step:\n2021 Aug -\n2022 Feb", ha="right", fontsize=7)
fig.suptitle("2MASS J16070852-3201009 (Upper Sco): the 3-5 µm excess vanished in 2021-22", fontsize=10)
fig.tight_layout()
fig.savefig("docs/briefs/figures/J160708_followup_2026-10-30.png", dpi=150)
