"""Cut the small tables that claims.py recomputes the note's numbers from, out of the H-0016 run directory
(~/oddsky-runs/h0016, too large for the repo: the 506,437-row IRSA pull is 143 MB). Run from the repo root.
Every output is a plain subset or a count of an input; nothing is fitted or adjusted here."""
import json
import os

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
big = pd.read_csv(RUN + "allwise_discrepant_all.csv", usecols=["w1mpro", "w1mag", "w1snr"])
counts = {
    "steps_all": len(pd.read_csv(RUN + "steps_raw.csv", usecols=["allwise_cntr"])),
    "steps_unflagged": len(pd.read_csv(RUN + "steps_clean.csv", usecols=["allwise_cntr"])),
    "discrepant_or_low_snr": int((((big.w1mag - big.w1mpro).abs() > 0.4) | (big.w1snr < 20)).sum()),
    "discrepant_rows": len(big),
    "discrepant_and_snr_below_15": int((((big.w1mag - big.w1mpro).abs() > 0.4) & (big.w1snr < 15)).sum()),
}
json.dump(counts, open(OUT + "counts.json", "w"), indent=1)
print(counts)

# Reject Table entries within 8" of the 48 (hunts/H-0016/scripts/reject_table.py and the first-pass pulls), with the Tile
# columns for the full-SNR ones, and one row per target saying whether its cone query succeeded
first = pd.concat([pd.read_csv(RUN + "aw_rejects.csv", dtype=str), pd.read_csv(RUN + "aw_rejects_rev.csv", dtype=str)]).drop_duplicates(["target", "designation"])
detail = pd.read_csv(RUN + "aw_rejects_detail.csv", dtype=str)[["designation", "coadd_id", "src", "wx", "wy", "use_src", "best_use_cntr"]].drop_duplicates()
zero = pd.read_csv(RUN + "rejects_zero_verify.csv", dtype=str)
first["designation_key"] = first.designation
rej = first.merge(detail, on="designation", how="left")
# the same star extracted in two Tiles has the same designation: keep the row from each Tile
status = pd.concat([pd.DataFrame({"target": sorted(set(first.target)), "status": "ok"}), zero[["target", "status"]].drop_duplicates()])
status["n_reject_entries"] = status.target.map(first.groupby("target").size()).fillna(0).astype(int)
status.to_csv(OUT + "reject_query_status_48.csv", index=False)
rej[["target", "designation", "sep", "w1mpro", "w1snr", "w1mag", "w1nm", "w1m", "nb", "cc_flags", "rel", "coadd_id", "src", "wx", "wy", "use_src", "best_use_cntr"]].to_csv(OUT + "reject_entries_48.csv", index=False)
full = pd.read_csv(RUN + "aw_fullrows.csv", dtype={"cntr": str})
full[["designation", "cntr", "coadd_id", "src", "wx", "wy", "pmcode", "rel"]].to_csv(OUT + "catalog_tiles_48.csv", index=False)

# the same for the 40 image-validated sources of the list (4" cones)
t = pd.read_csv(RUN + "tierA_rejects.csv", dtype=str)
F = pd.read_csv("hunts/H-0016/work/allwise_profile_fit_failures.csv", dtype={"cntr": str})[["cntr", "ra", "dec", "w1mag", "w1mpro"]]
t = t.merge(F.rename(columns={"cntr": "target_cntr", "ra": "t_ra", "dec": "t_dec", "w1mag": "t_w1mag", "w1mpro": "t_w1mpro"}), on="target_cntr")
t.to_csv(OUT + "reject_entries_listed40.csv", index=False)
print(len(status), "targets with a reject-query status;", int((status.status != "ok").sum()), "failed")
