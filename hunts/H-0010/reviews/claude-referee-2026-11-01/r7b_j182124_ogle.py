"""r7b: J182124.77-190909.7 (Gaia DR3 4096047127002546560) = OGLE-IV GVS BLG783.17.33659, listed by Mroz et al. 2020 (ApJS 249,
16; Table B2 'possible microlensing events'; VizieR J/ApJS/249/16/tableb2). Downloads OGLE's public I-band light curve (data,
read only) and compares the 2015 brightening with the Gaia DR3 G transits. Run: uv run python -I hunts/H-0010/reviews/claude-referee-2026-11-01/r7b_j182124_ogle.py"""
import io, os
import numpy as np, pandas as pd, requests
HERE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(HERE, "data", "ogle_dl", "BLG783.17.33659.dat")
if not os.path.exists(p):
    r = requests.get("https://www.astrouw.edu.pl/ogle/ogle4/galactic_disk_microlensing/data_c/BLG783.17.33659.dat", timeout=120)
    r.raise_for_status(); open(p, "w").write(r.text)
o = pd.read_csv(p, sep=r"\s+", header=None, usecols=[0, 1, 2], names=["hjd", "I", "e"])
o["mjd"] = o.hjd - 2400000.5
base = o[(o.mjd < 57150) | (o.mjd > 57350)].I.median()
print(f"OGLE: {len(o)} points MJD {o.mjd.min():.0f}-{o.mjd.max():.0f}; baseline I {base:.3f}")
ev = o[(o.mjd > 57150) & (o.mjd < 57350)]
for x in ev.itertuples():
    print(f"  MJD {x.mjd:.2f} I {x.I:.3f} dI {x.I - base:+.3f} (x{10 ** (-0.4 * (x.I - base)):.2f})")
g = pd.read_csv(os.path.join(HERE, "data", "epoch_raw", "4096047127002546560.csv"))
g["mjd"] = g.g_transit_time + 55197
gb = np.nanmedian(g.g_transit_flux)
print("Gaia G transits 2015 May-Dec:")
for x in g[(g.mjd > 57150) & (g.mjd < 57380)].itertuples():
    print(f"  MJD {x.mjd:.2f} G x{x.g_transit_flux / gb:.3f}")
