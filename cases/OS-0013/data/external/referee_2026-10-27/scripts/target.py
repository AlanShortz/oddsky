import sys, numpy as np, pandas as pd
from astropy.io import ascii as aascii
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 500)
f, ra0, dec0, pmra, pmdec = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
d = aascii.read(f, format="ipac").to_pandas()
# gaia position at epoch 2016 propagate
yr = 2016.0 + (d.mjd - 57388.5) / 365.25
sra = ra0 + pmra / 3.6e6 / np.cos(np.radians(dec0)) * (yr - 2016.0); sdec = dec0 + pmdec / 3.6e6 * (yr - 2016.0)
d["dra"] = (d.ra - sra) * np.cos(np.radians(dec0)) * 3600; d["ddec"] = (d.dec - sdec) * 3600
d["sep"] = np.hypot(d.dra, d.ddec)
t = d[d.sep < 4].sort_values("mjd").copy()
t["visit"] = (t.mjd.diff() > 30).cumsum()
good = (t.qual_frame > 0) & (t.qi_fact > 0) & (t.saa_sep > 0) & (t.moon_masked.astype(str).str.zfill(2) == "00")
t["good"] = good
g = t.groupby("visit").agg(t=("mjd", "median"), n=("mjd", "size"), ngood=("good", "sum"), w1=("w1mpro", "median"), w2=("w2mpro", "median"),
    dra=("dra", "median"), ddec=("ddec", "median"), w1rchi2=("w1rchi2", "median"), w2rchi2=("w2rchi2", "median"),
    nb_max=("nb", "max"), w1sky=("w1sky", "median"), w2sky=("w2sky", "median"),
    cc=("cc_flags", lambda x: ",".join(sorted(set(map(str, x))))), ph=("ph_qual", lambda x: ",".join(sorted(set(map(str, x))))),
    sat1=("w1sat", "max"), sat2=("w2sat", "max"), sso=("sso_flg", "max"))
print(g.round(3).to_string())
t.to_csv(f + ".target.csv", index=False)
