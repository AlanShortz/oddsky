"""p5: Gaia DR3 G scatter (fractional CCD-level flux rms = e_FG*sqrt(N)/FG, N = o_Gmag) of each target vs every DR3 star
within 3' and +-0.5 mag in G (VizieR I/355/gaiadr3, idia mirror). An event inside 2014-07-25..2017-05-28 that Gaia saw
inflates it. Also the excess rms over the field median, in flux fraction."""
import io
import os
import sys

import httpx
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from targets import HERE, T  # noqa: E402

rows = []
for k, t in T.items():
    q = httpx.get("https://vizier.idia.ac.za/viz-bin/asu-tsv", params={
        "-source": "I/355/gaiadr3", "-c": f"{t['ra']} {t['dec']}", "-c.rs": 180, "-out": "Source,Gmag,FG,e_FG,o_Gmag,RUWE",
        "Gmag": f"{t['G'] - 0.5}..{t['G'] + 0.5}", "-out.max": 20000}, timeout=300, headers={"User-Agent": "oddsky/0.1"})
    lines = [ln for ln in q.text.splitlines() if ln and not ln.startswith("#")]
    df = pd.read_csv(io.StringIO("\n".join([lines[0]] + lines[3:])), sep="\t", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    df["Source"] = df.Source.str.strip()
    for c in ("Gmag", "FG", "e_FG", "o_Gmag", "RUWE"):
        df[c] = pd.to_numeric(df[c].str.strip(), errors="coerce")
    df = df.dropna(subset=["FG", "e_FG", "o_Gmag"])
    df["rms"] = df.e_FG * np.sqrt(df.o_Gmag) / df.FG
    me = df[df.Source == t["gaia"]]
    if me.empty:
        print(k, "target not returned")
        continue
    r0 = float(me.rms.iloc[0])
    oth = df[df.Source != t["gaia"]]
    pct = 100 * (oth.rms < r0).mean()
    med = float(oth.rms.median())
    pct_ruwe = 100 * (oth[oth.RUWE < 1.4].rms < r0).mean()
    exc = float(np.sqrt(max(r0**2 - med**2, 0)))
    print(f"{k}: rms {r0:.4f} vs field median {med:.4f} (n {len(oth)}); percentile {pct:.1f} (RUWE<1.4 stars: {pct_ruwe:.1f}); "
          f"excess rms {exc:.4f}; 90/95/99th pct {np.percentile(oth.rms, 90):.4f}/{np.percentile(oth.rms, 95):.4f}/{np.percentile(oth.rms, 99):.4f}")
    rows.append(dict(k=k, rms=r0, field_median=med, pct=pct, excess=exc, p90=np.percentile(oth.rms, 90), p99=np.percentile(oth.rms, 99)))
pd.DataFrame(rows).to_csv(os.path.join(HERE, "dr3_scatter.csv"), index=False)
