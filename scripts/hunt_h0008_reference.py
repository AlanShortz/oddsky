"""H-0008: one table of known microlensing events to match against: KMTNet (2016-2024), OGLE EWS (2014-2025), OGLE GVS Galactic-disk events (Mroz et al. 2020), Gaia DR3
vari_microlensing (2014-2017), the ZTF catalogue of Zhai et al. 2024 (all 177, from the ApJ machine-readable tables), TNS
microlensing candidates found during refereeing (ext/tns_reported.csv), Rodriguez et al. 2022 and Medford et al. 2023 (positions only, no t0), and Gaia Science Alerts classified or described as microlensing (2016-2025; no tE, so a
100-day window is used). usage: hunt_h0008_reference.py EXT_DIR GAIA_ALERTS_CSV OUT_CSV"""

import sys

import pandas as pd

ext = sys.argv[1]
k = pd.read_csv(f"{ext}/kmt_events.csv").assign(source="KMTNet", mag=lambda d: d.I_base)
o = pd.read_csv(f"{ext}/ogle_events.csv").assign(source="OGLE", mag=lambda d: d.I_base)
v = pd.read_csv(f"{ext}/ogle_gvs_mroz2020.csv").assign(source="OGLE GVS (Mroz+2020)", mag=lambda d: d.I_base)
g = pd.read_csv(f"{ext}/gaia_dr3_microlensing.csv", dtype={"source_id": str})
g = g.assign(name="Gaia DR3 " + g.source_id, source="Gaia DR3", mag=g.G)
a = pd.read_csv(sys.argv[2], skipinitialspace=True)
a.columns = [c.strip("# ") for c in a.columns]
lens = a[a.Class.astype(str).str.contains("ULENS", case=False) | a.Comment.astype(str).str.contains("microlens", case=False)]
a = pd.DataFrame({"name": lens.Name, "ra": lens.RaDeg, "dec": lens.DecDeg,
                  "t0_mjd": pd.to_datetime(lens.Date).map(lambda d: d.to_julian_date() - 2400000.5), "tE": None, "u0": None,
                  "mag": lens.HistoricMag, "source": "Gaia alerts"})
z = pd.read_csv(f"{ext}/ztf_zhai2024.csv").assign(source="ZTF (Zhai+2024)", mag=None)
tn = pd.read_csv(f"{ext}/tns_reported.csv")  # microlensing candidates found on TNS during refereeing
zo = pd.read_csv(f"{ext}/ztf_older.csv").assign(t0_mjd=None, tE=None, u0=None, mag=None)  # positions only
cols = ["name", "ra", "dec", "t0_mjd", "tE", "u0", "mag", "source"]
out = pd.concat([k[cols], o[cols], v[cols], g[cols], a[cols], z[cols], tn[cols]], ignore_index=True)
out = pd.concat([out[out.t0_mjd.between(55000, 62000)], zo[cols]], ignore_index=True)
out.to_csv(sys.argv[3], index=False)
print(out.source.value_counts().to_dict())
