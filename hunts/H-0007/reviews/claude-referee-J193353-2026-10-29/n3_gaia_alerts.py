"""Referee J193353: nearest Gaia Science Alerts (hunts/H-0005/alerts.csv). uv run python .../n3_gaia_alerts.py"""
import numpy as np, pandas as pd

RA, DEC = 293.471115, -21.3037472
a = pd.read_csv("hunts/H-0005/alerts.csv")
a.columns = [c.strip().lstrip("#") for c in a.columns]
r1, d1, r2, d2 = map(np.radians, (RA, DEC, a.RaDeg.values, a.DecDeg.values))
a["sep_deg"] = np.degrees(2 * np.arcsin(np.sqrt(np.sin((d2 - d1) / 2) ** 2 + np.cos(d1) * np.cos(d2) * np.sin((r2 - r1) / 2) ** 2)))
a = a.sort_values("sep_deg")
print(f"{len(a)} alerts; date range {a.Date.min()} .. {a.Date.max()}")
cols = ["Name", "Date", "RaDeg", "DecDeg", "AlertMag", "HistoricMag", "Class", "sep_deg", "Comment"]
print("\nnearest 10:"); print(a[cols].head(10).to_string(index=False))
print("\nwithin 1 deg:", (a.sep_deg < 1).sum()); print(a.loc[a.sep_deg < 1, cols].to_string(index=False))
y = a[a.Date.str.startswith("2020")]
print("\n2020 alerts within 5 deg:"); print(y.loc[y.sep_deg < 5, cols].to_string(index=False))
print("\nnearest 2020 alert:"); print(y[cols].head(1).to_string(index=False))
