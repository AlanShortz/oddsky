"""s14: why are the catalogued lenses among the 67 not in Gaia DR3 vari_microlensing? Wyrzykowski et al. (2023, A&A 674, A23;
arXiv:2206.06121 sec. 4 and table 2): Sample B took OGLE-IV events with survey tE > 20 d and maximum between JD 2456863.94 and
2457901.86 (the DR3 span), recovered by the Extractor/MSOS pipeline (404 of 1074 matched sources) and kept on visual inspection
(233); Sample A (automated) required among others G0 < 19, 20 < tE < 300 d, |u0| < 1, 1 < BP-RP < 4, at least one tE inside the
data and an event duration > 135 d. This script tags each catalogued lens with the published criteria it fails.
Run from the repo root: uv run python -I hunts/H-0010/scripts/s14_dr3_cuts.py. Writes hunts/H-0010/data/dr3_cuts.csv."""
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, WORK  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
JD0, JD1 = 2456863.94 - 2400000.5, 2457901.86 - 2400000.5
t = pd.read_csv(os.path.join(WORK, "gaia_ml_unpub.csv"), dtype={"source_id": str})
ref = pd.read_csv(os.path.join(REPO, "hunts/H-0008/ext/reference_lenses.csv")).drop_duplicates("name").set_index("name")
rows = []
for r in t[t.verdict == "known lens"].itertuples():
    names = re.findall(r"(OGLE-\d{4}-BLG-\d{4})", str(r.ref_intime))
    why = []
    if not names:
        why.append("not an OGLE-IV event (Sample B drew on OGLE-IV)")
    else:
        x = ref.loc[names[0]]
        if x.tE <= 20:
            why.append(f"OGLE tE {x.tE:.1f} d <= 20 d (Sample B entry cut)")
        if not JD0 <= x.t0_mjd <= JD1:
            why.append("OGLE maximum outside the DR3 span (Sample B entry cut)")
    if "Gaia16aye" in str(r.known_as):
        why.append("binary lens with caustic crossings (no point-lens fit)")
    if why:  # not eligible for Sample B; note the Sample A cuts it also fails
        if r.base_G > 19:
            why.append(f"G baseline {r.base_G:.1f} > 19 (Sample A cut)")
        if r.bp_rp >= 4 or r.bp_rp <= 1:
            why.append(f"BP-RP {r.bp_rp:.2f} outside 1-4 (Sample A cut)")
    else:
        why.append("passes Sample B's entry cuts: lost at pipeline recovery or visual inspection (reasons not published)")
    rows.append(dict(source_id=r.source_id, known_as=r.known_as, dr3_exclusion="; ".join(why)))
d = pd.DataFrame(rows)
d.to_csv(os.path.join(DATA, "dr3_cuts.csv"), index=False)
print(d.to_string())
print((d.dr3_exclusion.str.startswith("passes")).sum(), "pass Sample B entry cuts")
