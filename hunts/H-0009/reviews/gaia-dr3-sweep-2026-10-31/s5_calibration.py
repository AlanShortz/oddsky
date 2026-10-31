"""s5: how informative is the absence of a Gaia DR3 VARIABLE flag? Calibration on the known lenses H-0009 recovered blind whose
NEOWISE event falls inside the DR3 epoch span. Events that are in the reference list only because Gaia DR3 catalogued them
(vari_microlensing requires a VARIABLE flag) are excluded from the unbiased fraction. For each: any VARIABLE Gaia DR3 source within
4" (VizieR idia), and within 1.5" of the matched star. Writes data/calib_known.csv."""
import io
import os
import sys
import time

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, DR3_T0, DR3_T1, H9, UA  # noqa: E402

k = pd.read_csv(os.path.join(H9, "work", "sky4_classified.csv"), dtype={"g_source_id": str, "allwise_cntr": str})
k = k[(k["class"] == "microlensing (known)") & (k.t > DR3_T0) & (k.t < DR3_T1)].copy()
k["gaia_selected"] = k.known_lens.fillna("").str.contains("Gaia DR3") & ~k.known_lens.fillna("").str.contains("OGLE|KMT")
rows = []
for r in k.itertuples():
    for i in range(5):
        try:
            q = requests.get("https://vizier.idia.ac.za/viz-bin/asu-tsv", params={
                "-source": "I/355/gaiadr3", "-c": f"{r.ra} {r.dec}", "-c.rs": 4, "-c.u": "arcsec", "-sort": "_r",
                "-out": "Source,Gmag,VarFlag", "-out.add": "_r"}, headers=UA, timeout=120)
            break
        except Exception:  # noqa: BLE001
            time.sleep(5 * (i + 1))
    lines = [ln for ln in q.text.splitlines() if ln and not ln.startswith("#")]
    g = pd.read_csv(io.StringIO("\n".join([lines[0]] + lines[3:])), sep="\t", dtype=str) if len(lines) > 3 else pd.DataFrame()
    g.columns = [c.strip() for c in g.columns]
    var = g[g.VarFlag.str.strip() == "VARIABLE"] if len(g) else g
    rows.append(dict(designation=r.designation, t=r.t, dw1=r.dw1, G=r.g_phot_g_mean_mag, gaia_selected=r.gaia_selected,
                     known=r.known_lens, n4=len(g), var4=len(var),
                     var_sep=";".join(var["_r"].str.strip()) if len(var) else "", matched_var=r.g_phot_variable_flag == "VARIABLE"))
c = pd.DataFrame(rows)
c.to_csv(os.path.join(DATA, "calib_known.csv"), index=False)
pd.set_option("display.width", 250)
print(c.drop(columns="known").round(2).to_string(index=False))
for sel, name in ((c.gaia_selected, "found via Gaia DR3 catalogue"), (~c.gaia_selected, "found by OGLE/KMT/GVS (unbiased)")):
    d = c[sel]
    print(f"{name}: {len(d)}; VARIABLE source within 4\": {(d.var4 > 0).sum()}; matched star VARIABLE: {d.matched_var.sum()}")
d = c[~c.gaia_selected]
for lo, hi in ((0, 0.5), (0.5, 1.0), (1.0, 9)):
    x = d[(-d.dw1 >= lo) & (-d.dw1 < hi)]
    print(f"  unbiased, |dW1| {lo}-{hi} mag: {len(x)}, VARIABLE within 4\": {(x.var4 > 0).sum()}")
