"""Centroid test: does the SPHEREx position of OS-0013 move between K (D3, 1.6-2.4 um) and W2-like (D6, 4.4-5.0 um)
images, relative to the comparison stars? Per image, the median offset of the comparison stars (WCS zero-point)
is subtracted. Usage: centroid_ana.py <phot_centroid.csv>"""
import sys, numpy as np, pandas as pd
d = pd.read_csv(sys.argv[1]); d = d[d.nbad_core == 0]
T = "J144351.92-761145.9"
zp = d[d.allwise != T].groupby("file")[["dra_as", "ddec_as"]].median()
d = d.join(zp, on="file", rsuffix="_zp")
d["ra_c"] = d.dra_as - d.dra_as_zp; d["de_c"] = d.ddec_as - d.ddec_as_zp
rows = []
for star, g in d.groupby("allwise"):
    r = {"allwise": star}
    for det in (3, 6):
        h = g[g.det == det]
        for c in ("ra_c", "de_c"):
            r[f"{c}_D{det}"] = h[c].mean(); r[f"e{c}_D{det}"] = h[c].std() / np.sqrt(len(h))
        r[f"n_D{det}"] = len(h)
    r["dRA_D6-D3"] = r["ra_c_D6"] - r["ra_c_D3"]; r["dDec_D6-D3"] = r["de_c_D6"] - r["de_c_D3"]
    r["err"] = np.sqrt(np.mean([r["era_c_D6"] ** 2 + r["era_c_D3"] ** 2, r["ede_c_D6"] ** 2 + r["ede_c_D3"] ** 2]))
    rows.append(r)
res = pd.DataFrame(rows).set_index("allwise")
pd.set_option("display.width", 250)
print(res[["n_D3", "n_D6", "ra_c_D3", "de_c_D3", "ra_c_D6", "de_c_D6", "dRA_D6-D3", "dDec_D6-D3", "err"]].round(3).to_string())
c = res.drop(T)
print(f"\ncomparison stars: D6-D3 shift rms RA {np.sqrt((c['dRA_D6-D3']**2).mean()):.3f}\", Dec {np.sqrt((c['dDec_D6-D3']**2).mean()):.3f}\"")
t = res.loc[T]
print(f"target: D6-D3 shift RA {t['dRA_D6-D3']:+.3f}\", Dec {t['dDec_D6-D3']:+.3f}\" (+-{t['err']:.3f}\" statistical)")
# expected shift if the W2 excess (~27% of the total 4.6 um flux) came from a neighbour instead of the target
for name, dra, dde in (("7.9\" Gaia ...473984", (220.960074 - 220.966318) * np.cos(np.radians(-76.196)) * 3600, (-76.197727 + 76.196117) * 3600),
                       ("13.4\" AllWISE J144348.59", (220.952280 - 220.966318) * np.cos(np.radians(-76.196)) * 3600, (-76.194500 + 76.196117) * 3600)):
    print(f"if the excess sat on {name}: expected D6 shift RA {0.27*dra:+.2f}\", Dec {0.27*dde:+.2f}\"")
