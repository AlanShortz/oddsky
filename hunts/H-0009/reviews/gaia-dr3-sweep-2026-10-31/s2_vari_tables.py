"""s2: Gaia DR3 variability tables for every source within 4" of a strong event.
Primary: VizieR copies of the DR3 variability tables (I/358, idia mirror), 4" cones around every event position:
varisum (= vari_summary: in_vari_* flags), vclassre (= vari_classifier_result) and vmicro (= vari_microlensing).
Cross-check: the ESA TAP (gaiadr3.vari_classifier_result, vari_summary, vari_microlensing) with IN() lists of 25 ids, short
timeouts; it hung for 40 min on the first attempt today, so a TAP failure is logged, not fatal (a table is abandoned at its
first failed chunk; `--no-tap` skips it).
phot_variable_flag and has_epoch_photometry come from s1 (I/355/gaiadr3 VarFlag, EpochPh). Writes data/vari_*.csv (ids as str)."""
import io
import os
import sys
import time

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, UA, cones, events, tap  # noqa: E402

ev = events()
cn = cones()


def viz(table, ra, dec):
    for k in range(5):
        try:
            q = requests.get("https://vizier.idia.ac.za/viz-bin/asu-tsv", params={
                "-source": f"I/358/{table}", "-c": f"{ra} {dec}", "-c.rs": 4, "-c.u": "arcsec", "-out": "**", "-out.add": "_r"},
                headers=UA, timeout=120)
            if q.status_code == 200:
                break
        except Exception as ex:  # noqa: BLE001
            print("retry", table, ex)
        time.sleep(5 * (k + 1))
    lines = [ln for ln in q.text.splitlines() if ln and not ln.startswith("#")]
    if len(lines) < 4:
        return pd.DataFrame()
    g = pd.read_csv(io.StringIO("\n".join([lines[0]] + lines[3:])), sep="\t", dtype=str)
    g.columns = [c.strip() for c in g.columns]
    return g.apply(lambda s: s.str.strip())


out = {"varisum": [], "vclassre": [], "vmicro": []}
for r in ev.itertuples():
    for t in out:
        g = viz(t, r.ra, r.dec)
        if len(g):
            g.insert(0, "designation", r.designation)
            out[t].append(g)
for t, parts in out.items():
    d = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["designation", "Source"])
    d = d.rename(columns={"Source": "source_id"})
    d.to_csv(os.path.join(DATA, f"vari_{t}.csv"), index=False)
    print(f"VizieR I/358/{t}: {len(d)} rows within 4\" of {d.designation.nunique()} events")
    if len(d):
        keep = [c for c in ["designation", "_r", "source_id", "Classifier", "Class", "ClassSc", "NG", "Gmagmed", "Gmagmin", "Gmagmax",
                            "VCR", "Vmicro", "VLPV", "VST", "VEB", "teP0", "TmaxP0", "u0P0"] if c in d.columns]
        print(d[keep].to_string(index=False))
missing = set(cn.source_id[cn.VarFlag == "VARIABLE"]) - set(pd.read_csv(os.path.join(DATA, "vari_varisum.csv"), dtype=str).source_id)
print("VARIABLE sources (s1) missing from varisum:", missing or "none")

# ESA TAP cross-check (skip with --no-tap)
if "--no-tap" in sys.argv:
    sys.exit()
ids = sorted(cn.source_id.unique())
for name, q in {
    "vari_classifier_result": "SELECT source_id, classifier_name, best_class_name, best_class_score FROM gaiadr3.vari_classifier_result WHERE source_id IN ({})",
    "vari_microlensing": "SELECT source_id, paczynski0_te, paczynski0_tmax FROM gaiadr3.vari_microlensing WHERE source_id IN ({})",
    "vari_summary": "SELECT source_id, in_vari_classification_result, in_vari_microlensing FROM gaiadr3.vari_summary WHERE source_id IN ({})",
}.items():
    try:
        d = pd.concat([tap(q.format(",".join(ids[i:i + 25])), tries=2, timeout=120) for i in range(0, len(ids), 25)], ignore_index=True)
        d.to_csv(os.path.join(DATA, f"tap_{name}.csv"), index=False)
        print(f"ESA TAP {name}: {len(d)} rows for {len(ids)} ids")
        if len(d):
            print(d.to_string(index=False))
    except Exception as ex:  # noqa: BLE001
        print(f"ESA TAP {name} failed: {str(ex)[:200]}")
