"""r8: the investigators' claim that 21 of the 28 catalogued lenses 'pass Sample B's published entry cuts'.
Wyrzykowski et al. 2023 (arXiv:2206.06121, sec. 4.2) built Sample B from the OGLE-IV event lists of Mroz et al. 2019 (bulge,
J/ApJS/244/29) and Mroz et al. 2020b (disc, J/ApJS/249/16) -- not from the OGLE EWS -- plus 2 ASAS-SN events and 7 Gaia alerts;
tE > 20 d, maximum inside JD 2456863.9375-2457901.86389, DR3 match within 0.5"; then Extractor/MSOS recovery (404 of 1074) and
visual inspection (>= 2 points in the brightening) -> 233.
This script queries every table of J/ApJS/244/29 and J/ApJS/249/16 within 3" of each of the 28 known lenses (VizieR idia mirror,
CDS fallback) and records membership, tE, t0 and the OGLE-Gaia separation. Writes data/sampleB.csv.
Run: uv run python -I hunts/H-0010/reviews/claude-referee-2026-11-01/r8_sampleB.py"""
import io, os, time
import numpy as np, pandas as pd, requests

HERE = os.path.dirname(os.path.abspath(__file__))
inv = pd.read_csv(os.path.join(HERE, "..", "..", "work", "gaia_ml_unpub.csv"), dtype={"source_id": str})
cuts = pd.read_csv(os.path.join(HERE, "..", "..", "data", "dr3_cuts.csv"), dtype={"source_id": str}).set_index("source_id")
K = inv[inv.verdict == "known lens"]
VIZ = ["https://vizier.idia.ac.za/viz-bin/asu-tsv", "https://vizier.cds.unistra.fr/viz-bin/asu-tsv"]
JD0, JD1 = 2456863.9375, 2457901.86389


def viz(cat, ra, dec, r):
    last = "?"
    for base in VIZ:
        for attempt in range(2):
            try:
                q = requests.get(base, params={"-source": cat, "-c": f"{ra} {dec}", "-c.rs": r, "-out": "**", "-out.add": "_r", "-out.max": 20},
                                 timeout=200)
                if "#INFO" not in q.text:
                    last = f"HTTP {q.status_code}"; continue
                blocks, cur = [], []
                for ln in q.text.splitlines():
                    if ln.startswith("#RESOURCE") or ln.startswith("#Table"):
                        if cur: blocks.append(cur)
                        cur = []
                    elif ln and not ln.startswith("#"):
                        cur.append(ln)
                if cur: blocks.append(cur)
                out = []
                for b in blocks:
                    if len(b) >= 3:
                        out.append(pd.read_csv(io.StringIO("\n".join([b[0]] + b[3:])), sep="\t"))
                return out, f"ok ({base.split('/')[2]})"
            except Exception as e:  # noqa: BLE001
                last = type(e).__name__
                time.sleep(5)
    return None, "UNKNOWN " + last


rows = []
for r in K.itertuples():
    rec = dict(source_id=r.source_id, known_as=cuts.loc[r.source_id, "known_as"] if r.source_id in cuts.index else "",
               inv_reason=cuts.loc[r.source_id, "dr3_exclusion"][:40] if r.source_id in cuts.index else "")
    for lab, cat in (("mroz2019", "J/ApJS/244/29"), ("mroz2020", "J/ApJS/249/16")):
        t, st = viz(cat, r.ra, r.dec, 3)
        if t is None:
            rec[lab] = st; continue
        hits = []
        for d in t:
            if len(d):
                cols = {c.lower(): c for c in d.columns}
                te = next((d[cols[c]].iloc[0] for c in ("te", "t_e", "tau") if c in cols), np.nan)
                t0 = next((d[cols[c]].iloc[0] for c in ("t0", "tmax", "t_0") if c in cols), np.nan)
                nm = next((d[cols[c]].iloc[0] for c in ("star", "id", "field", "name", "ews") if c in cols), "?")
                hits.append(f"{nm} tE={te} t0={t0} r={d['_r'].iloc[0]}\"")
        rec[lab] = "; ".join(hits) if hits else f"none [{st}]"
    rows.append(rec)
    print(rec, flush=True)
pd.DataFrame(rows).to_csv(os.path.join(HERE, "data", "sampleB.csv"), index=False)
