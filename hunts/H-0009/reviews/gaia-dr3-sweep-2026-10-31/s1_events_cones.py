"""s1: the deduplicated strong events (H-0008 sky3_strong 66 + H-0009 sky4_strong 122 minus 10 frame artifacts), joined to the
H-0009 referee's centroid test (r9b_flags), and every Gaia DR3 source within 4" of each AllWISE position (VizieR idia mirror,
I/355/gaiadr3). Writes data/events.csv and data/cones.csv (source_id kept as str)."""
import io
import os
import sys
import time

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, H8, H9, REF, UA  # noqa: E402

a = pd.read_csv(os.path.join(H8, "work", "sky3_strong.csv"), dtype={"g_source_id": str, "allwise_cntr": str})
b = pd.read_csv(os.path.join(H9, "work", "sky4_strong.csv"), dtype={"g_source_id": str, "allwise_cntr": str})
print(f"H-0008 strong {len(a)}, H-0009 strong {len(b)} ({int(b.frame_artifact.sum())} frame artifacts dropped)")
art = b[b.frame_artifact]
b = b[~b.frame_artifact].copy()
a_art = a[a.allwise_cntr.isin(art.allwise_cntr)]
print(f"H-0008 strong events that H-0009's referee calls frame artifacts: {len(a_art)}")
keep = ["allwise_cntr", "designation", "t", "dw1", "dw2", "ra", "dec", "l", "b", "w1mpro", "g_source_id", "g_sep",
        "g_phot_g_mean_mag", "n_gaia_3as"]
e9 = b[keep + ["nblock", "t_first", "t_last", "off_target"]].copy()
e9["in9"] = True
e8 = a[~a.allwise_cntr.isin(art.allwise_cntr)][keep].rename(columns={"t": "t_h8", "dw1": "dw1_h8"}).copy()
e8["in8"] = True
ev = e9.merge(e8[["allwise_cntr", "t_h8", "dw1_h8", "in8"]], on="allwise_cntr", how="outer")
only8 = e8[~e8.allwise_cntr.isin(e9.allwise_cntr)]
for c in keep:
    if c in ("t", "dw1", "allwise_cntr"):
        continue
    ev.loc[ev.allwise_cntr.isin(only8.allwise_cntr), c] = ev.loc[ev.allwise_cntr.isin(only8.allwise_cntr), "allwise_cntr"].map(only8.set_index("allwise_cntr")[c])
ev["t"] = ev.t.fillna(ev.t_h8)
ev["dw1"] = ev.dw1.fillna(ev.dw1_h8)
ev["in8"] = ev.in8.eq(True)
ev["in9"] = ev.in9.eq(True)
ev["hunts"] = np.where(ev.in8 & ev.in9, "H-0008+H-0009", np.where(ev.in9, "H-0009", "H-0008"))
print(f"deduplicated: {len(ev)} events ({(ev.hunts == 'H-0008+H-0009').sum()} in both, {(ev.hunts == 'H-0009').sum()} H-0009 only, "
      f"{(ev.hunts == 'H-0008').sum()} H-0008 only)")
dt = (ev.t - ev.t_h8).abs()
for r in ev[dt > 1].itertuples():
    print(f"  {r.designation}: H-0009 peak t {r.t:.1f}, H-0008 event t {r.t_h8:.1f} (both analysed)")
# H-0008-only events: what did H-0009 make of them?
c9 = pd.read_csv(os.path.join(H9, "work", "sky4_classified.csv"), dtype={"allwise_cntr": str})
for r in ev[ev.hunts == "H-0008"].itertuples():
    m = c9[c9.allwise_cntr == r.allwise_cntr]
    print(f"  H-0008 only: {r.designation} t {r.t:.1f} dw1 {r.dw1:.2f}; in sky4_classified: "
          + (", ".join(f"class {x['class']}, dw1 {x.dw1:.2f}, dw2 {x.dw2:.2f}, t {x.t:.1f}" for _, x in m.iterrows()) if len(m) else "no"))
f = pd.read_csv(os.path.join(REF, "r9b_flags.csv"), dtype={"cntr": str})
f = f[f.grp == "strong"]
cols = ["ox", "oy", "sx", "sy", "ra0", "de0", "shift", "shift_sig", "shift_pa", "miss", "miss_sig", "d_all", "off_target"]
ev = ev.merge(f[["cntr"] + cols].rename(columns={"cntr": "allwise_cntr", "off_target": "off_target_r9b"}), on="allwise_cntr", how="left")
ev["off_target"] = ev.off_target.astype(object).where(ev.off_target.notna(), ev.off_target_r9b)
ev = ev.sort_values("t").reset_index(drop=True)
ev.to_csv(os.path.join(DATA, "events.csv"), index=False)
print(f"in the DR3 epoch span (56863-57900): {((ev.t > 56863) & (ev.t < 57900)).sum()}; with centroid test: {ev.ox.notna().sum()}; "
      f"off-target: {(ev.off_target == True).sum()}")

out = []
for r in ev.itertuples():
    for k in range(5):
        try:
            q = requests.get("https://vizier.idia.ac.za/viz-bin/asu-tsv", params={
                "-source": "I/355/gaiadr3", "-c": f"{r.ra} {r.dec}", "-c.rs": 4, "-c.u": "arcsec", "-sort": "_r",
                "-out": "Source,RA_ICRS,DE_ICRS,Gmag,BPmag,RPmag,BP-RP,VarFlag,EpochPh,o_Gmag,RFG,RUWE,Plx,pmRA,pmDE",
                "-out.add": "_r", "-out.max": 100}, headers=UA, timeout=120)
            if q.status_code == 200:
                break
        except Exception as ex:  # noqa: BLE001
            print("retry", r.designation, ex)
        time.sleep(5 * (k + 1))
    lines = [ln for ln in q.text.splitlines() if ln and not ln.startswith("#")]
    if len(lines) < 4:
        print(f"  {r.designation}: no Gaia DR3 source within 4\"")
        continue
    g = pd.read_csv(io.StringIO("\n".join([lines[0]] + lines[3:])), sep="\t", dtype=str)
    g.columns = [c.strip() for c in g.columns]
    g = g.apply(lambda s: s.str.strip())
    g = g.rename(columns={"_r": "sep", "Source": "source_id", "BP-RP": "BPRP"})
    g.insert(0, "allwise_cntr", r.allwise_cntr)
    g.insert(1, "designation", r.designation)
    out.append(g)
c = pd.concat(out, ignore_index=True)
for k in ["sep", "RA_ICRS", "DE_ICRS", "Gmag", "BPmag", "RPmag", "BPRP", "o_Gmag", "RFG", "RUWE", "Plx", "pmRA", "pmDE"]:
    c[k] = pd.to_numeric(c[k], errors="coerce")
c["EpochPh"] = c.EpochPh.astype(int)
assert c.source_id.str.fullmatch(r"\d+").all()
c.to_csv(os.path.join(DATA, "cones.csv"), index=False)
print(f"{len(c)} Gaia DR3 sources within 4\" of {c.allwise_cntr.nunique()} events; {c.source_id.nunique()} unique; "
      f"VARIABLE {(c.VarFlag == 'VARIABLE').sum()}; with epoch photometry {c.EpochPh.sum()}")
