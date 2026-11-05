"""Cut the small tables that claims.py recomputes the note's numbers from, out of the H-0016 run directory
(~/oddsky-runs/h0016, too large for the repo: the 506,437-row IRSA pull is 143 MB). Run from the repo root.
Every output is a plain subset or a count of an input; nothing is fitted or adjusted here."""
import json
import os

import numpy as np
import pandas as pd

RUN = os.path.expanduser("~/oddsky-runs/h0016/")
OUT = "docs/papers/rnaas_allwise/data/"
stars = pd.read_csv("docs/papers/rnaas_allwise/dbf_48_unflagged_stars.csv")

# catalogue columns of the 48 that are not in the data-behind-the-figure file
m = pd.read_csv(RUN + "steps_mep_epochs.csv", dtype={"cntr": str, "cc_flags": str})
m = m[m.designation.isin(stars.designation)]
m[["designation", "cntr", "sigra", "sigdec", "pmra", "pmdec", "cc_flags", "nb", "na", "ext_flg", "w1rchi2"]].to_csv(OUT + "catalog_columns_48.csv", index=False)

# AllWISE Multiepoch Photometry rows of the 48
mep = pd.read_csv(RUN + "steps_mep.csv", dtype={"cntr_mf": str})
mep = mep[mep.cntr_mf.isin(m.cntr)].merge(m[["cntr", "designation"]], left_on="cntr_mf", right_on="cntr")
mep[["designation", "mjd", "w1mpro_ep", "w1sigmpro_ep", "w1rchi2_ep", "w1flux_ep"]].to_csv(OUT + "mep_48.csv", index=False)

# Gaia neighbours: within 8.5" (pairs) and within 15"
a = pd.read_csv(RUN + "artifacts_classified.csv")
g = pd.read_csv(RUN + "gaia15.csv")
a[["designation", "pair", "nb_sep", "nb_dG", "second_entry_sep"]].merge(
    g[["designation", "status", "n_nb_bright"]], on="designation", how="outer").to_csv(OUT + "neighbours_48.csv", index=False)

# control sample (1.5-deg cone at |b| = 80)
pd.read_csv(RUN + "control_cone.csv").to_csv(OUT + "control_cone.csv", index=False)

# counts from the large pulls
big = pd.read_csv(RUN + "allwise_discrepant_all.csv", usecols=["w1mpro", "w1mag", "w1snr", "w1nm", "w1m", "k_m_2mass"])
snr_exp = np.interp(big.w1mpro, [8.0, 12.5, 13.0, 13.5, 14.0, 14.5, 16.0], [47.5, 47.5, 45.6, 44.0, 41.5, 38.9, 31.4])  # oddsky.data.allwise
n_fail = (((big.w1mag - big.w1mpro).abs() > 0.3).astype(int) + (big.w1snr < 0.5 * snr_exp)
          + ((big.w1nm / big.w1m.replace(0, np.nan)).fillna(1) < 0.6))
two = big[n_fail >= 2]
dk_ap, dk_pro = (two.k_m_2mass - two.w1mag).abs(), (two.k_m_2mass - two.w1mpro).abs()
counts = {
    "steps_all": len(pd.read_csv(RUN + "steps_raw.csv", usecols=["allwise_cntr"])),
    "steps_unflagged": len(pd.read_csv(RUN + "steps_clean.csv", usecols=["allwise_cntr"])),
    "discrepant_or_low_snr": int((((big.w1mag - big.w1mpro).abs() > 0.4) | (big.w1snr < 20)).sum()),
    "discrepant_rows": len(big),
    "discrepant_and_snr_below_15": int((((big.w1mag - big.w1mpro).abs() > 0.4) & (big.w1snr < 15)).sum()),
    "fail_two_of_three_tests": len(two),
    "two_fail_k_favors_profile": int(((dk_pro < 0.4) & (dk_ap > 0.4)).sum()),
    "two_fail_k_favors_aperture": int(((dk_ap < 0.4) & (dk_pro > 0.4)).sum()),
}
json.dump(counts, open(OUT + "counts.json", "w"), indent=1)
print(counts)

# Reject Table entries within 8" of the 48 and the Catalog rows of the 48, one status-tracked IRSA query per target
# (hunts/H-0016/scripts/reject_table.py and catalog_rows.py, 2026-11-05). Identifiers stay strings.
rej = pd.read_csv(RUN + "rejects_48_final.csv", dtype=str)
status = rej.groupby("target").agg(status=("status", "first"), n_reject_entries=("designation", "count")).reset_index()
status.to_csv(OUT + "reject_query_status_48.csv", index=False)
# separation of each Reject entry from the star's Gaia DR3 position propagated to 2010.5 (is it the same star?)
gaia = pd.read_csv(OUT + "gaia_positions_48.csv").set_index("designation")
for col in ("ra", "dec", "sep", "wx", "wy"):
    rej[col] = rej[col].astype(float)
dt = 2010.5 - 2016.0
g_dec = rej.target.map(gaia.dec) + rej.target.map(gaia.pmdec.fillna(0)) * dt / 3.6e6
g_ra = rej.target.map(gaia.ra) + rej.target.map(gaia.pmra.fillna(0)) * dt / 3.6e6 / np.cos(np.radians(g_dec))
rej["gaia_sep"] = (3600 * np.hypot((rej.ra - g_ra) * np.cos(np.radians(rej.dec)), rej.dec - g_dec)).round(3)
rej[rej.designation.notna()][["target", "designation", "cntr", "sep", "gaia_sep", "w1mpro", "w1snr", "w1mag", "w1nm", "w1m", "nb", "cc_flags", "rel",
                              "coadd_id", "src", "wx", "wy", "use_src", "best_use_cntr"]].to_csv(OUT + "reject_entries_48.csv", index=False)
cat = pd.read_csv(RUN + "catalog_48_final.csv", dtype=str)
assert (cat.status == "ok").all() and len(cat) == 48
cat[["designation", "cntr", "coadd_id", "src", "wx", "wy", "rel", "ph_qual", "pmcode"]].to_csv(OUT + "catalog_tiles_48.csv", index=False)

# the same for the 40 image-validated sources of the list (4" cones)
t = pd.read_csv(RUN + "tierA_rejects.csv", dtype=str)
F = pd.read_csv("hunts/H-0016/work/allwise_profile_fit_failures.csv", dtype={"cntr": str})[["cntr", "ra", "dec", "w1mag", "w1mpro"]]
t = t.merge(F.rename(columns={"cntr": "target_cntr", "ra": "t_ra", "dec": "t_dec", "w1mag": "t_w1mag", "w1mpro": "t_w1mpro"}), on="target_cntr")
t.to_csv(OUT + "reject_entries_listed40.csv", index=False)
print(len(status), "targets with a reject-query status;", int((status.status != "ok").sum()), "failed")
