"""e6: the sample table of dr4_ensemble.md section 1.4, from dr4_ensemble_sample.csv (run after e4).
Run from the repo root:  uv run python -I hunts/H-0009/predictions/work/ensemble/e6_table.py  -> work/ensemble/sample_table.md"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PRED = os.path.abspath(os.path.join(HERE, "..", ".."))
s = pd.read_csv(os.path.join(PRED, "dr4_ensemble_sample.csv"), dtype={"source_id": str, "alt_source_id": str})
SHORT = {"J163539": "ATLAS: achromatic x6-9", "J173150": "ATLAS: x7.7, months", "J075219": "ATLAS: real month-long rise",
         "J185846": "ATLAS: Gaia star not the variable", "J182120": "ATLAS: IR variable (YSO?)", "J075928": "ATLAS unusable",
         "J170153": "ATLAS flat: IR-only", "J185035": "ATLAS flat: IR-only", "J173349": "no ATLAS; no OGLE alert"}
lines = ["| # | event | case | NEOWISE visit (MJD, date) | abs dW1 | visits | tested Gaia DR3 source_id | sep (\") | G | BP-RP | "
         "centroid | DR3 span | GOST transits within 30 d (nearest, d) | optical info | P(pass) |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for i, r in enumerate(s.itertuples(), 1):
    off = {"True": "off-target", "False": "on"}.get(str(r.off_target), "no test")
    if isinstance(r.alt_source_id, str) and r.alt_source_id:
        off += f"; points at {r.alt_source_id} ({r.alt_sep_arcsec:.2f}\")"
    pp = "untestable by design" if r.status != "testable" else f"{r.p_pass_forecast:.2f}"
    bprp = "" if not np.isfinite(r.bp_rp) else f"{r.bp_rp:.2f}"
    case = r.case if isinstance(r.case, str) else ""
    lines.append(f"| {i} | {r.designation} | {case} | {r.t_event_mjd:.3f} ({r.event_date}) | {r.abs_dw1:.2f} | {r.nblock} | "
                 f"{r.source_id} | {r.sep_arcsec:.2f} | {r.G:.2f} | {bprp} | {off} | {'yes' if r.in_dr3_span else 'no'} | "
                 f"{r.gost_n_fov_30} ({r.gost_nearest_d:.1f}) | {SHORT.get(r.designation[:7], '')} | {pp} |")
open(os.path.join(HERE, "sample_table.md"), "w").write("\n".join(lines) + "\n")
print(f"{len(s)} rows -> work/ensemble/sample_table.md")
