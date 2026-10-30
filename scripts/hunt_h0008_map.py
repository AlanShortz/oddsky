"""H-0008 figure: the whole sky as NEOWISE searched it (stars with >= 10 visits per HEALPix pixel, Galactic Aitoff), with the
vetted one-visit brightenings on top, coloured by what they turned out to be.
usage: hunt_h0008_map.py REPORTS_DIR VETTED_CSV OUT_PNG
"""

import glob
import json
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import astropy.units as u
import matplotlib.pyplot as plt
from astropy.coordinates import SkyCoord
from astropy_healpix import HEALPix

rep = pd.DataFrame([json.load(open(f)) for f in glob.glob(f"{sys.argv[1]}/*.json")])
rep = rep[rep.status == "ok"]
hp = HEALPix(nside=32, order="nested")
ra, dec = hp.healpix_to_lonlat(rep.pixel.to_numpy())
g = SkyCoord(ra, dec).galactic
lon = -np.radians(((g.l.deg + 180) % 360) - 180)
lat = np.radians(g.b.deg)
v = pd.read_csv(sys.argv[2])
fig = plt.figure(figsize=(14, 7.5))
ax = fig.add_subplot(111, projection="aitoff")
sc = ax.scatter(lon, lat, c=np.log10(rep.stars.clip(lower=1)), s=4, cmap="Greys", vmin=3, vmax=5, marker="s", linewidths=0)
style = {"microlensing (new)": ("crimson", 140, "*"), "microlensing (known)": ("darkorange", 90, "*"),
         "dwarf nova / CV": ("royalblue", 30, "o"), "young star": ("seagreen", 30, "o"), "other variable": ("0.4", 20, "o"),
         "unclassified": ("purple", 25, "D")}
for cls, (col, size, mk) in style.items():
    w = v[v["class"] == cls]
    if len(w):
        gg = SkyCoord(w.ra.to_numpy() * u.deg, w.dec.to_numpy() * u.deg).galactic
        ax.scatter(-np.radians(((gg.l.deg + 180) % 360) - 180), np.radians(gg.b.deg), c=col, s=size, marker=mk,
                   edgecolors="k", linewidths=0.4, label=f"{cls} ({len(w)})", zorder=3)
ax.grid(alpha=0.3)
ax.set_xticklabels(["150°", "120°", "90°", "60°", "30°", "0°", "330°", "300°", "270°", "240°", "210°"], fontsize=8)
ax.legend(loc="lower right", fontsize=8, bbox_to_anchor=(1.12, -0.05))
cb = plt.colorbar(sc, ax=ax, orientation="horizontal", fraction=0.04, pad=0.06)
cb.set_label("log10 stars searched per HEALPix pixel (≥ 10 NEOWISE visits)")
ax.set_title(f"H-0008: {int(rep.stars.sum()) / 1e6:.0f} million stars, NEOWISE 2014-2024, one-night achromatic brightenings", pad=18)
plt.savefig(sys.argv[3], dpi=110, bbox_inches="tight")
print("pixels", len(rep), "stars", int(rep.stars.sum()))
