"""ATLAS nightly weighted fluxes 2020-04 to 2021-05 at the position, and per-unit (camera) baseline offsets."""
import io
from pathlib import Path
import numpy as np
import pandas as pd
HERE = Path(__file__).resolve().parent
d = pd.read_csv(io.StringIO((HERE / "atlas" / "atlas_5280891.txt").read_text().lstrip("#")), sep=r"\s+")
d = d[(d.duJy > 0) & (d.duJy < 150) & (d["chi/N"] < 5) & (d.err == 0)]
d["night"] = np.floor(d.MJD); d["cam"] = d.Obs.str[:3]
s = d[(d.MJD > 58960) & (d.MJD < 59340)]
g = s.groupby(["night", "F", "cam"]).apply(lambda x: pd.Series(dict(m=np.average(x.uJy, weights=1 / x.duJy ** 2), e=1 / np.sqrt((1 / x.duJy ** 2).sum()),
    n=len(x), m5=x.mag5sig.median())), include_groups=False).reset_index()
pd.set_option("display.width", 200)
print(g.round(2).to_string())
for (cam, f), x in d.groupby(["cam", "F"]):
    for a, b, lab in ((57200, 58970, "pre"), (59400, 61100, "post")):
        y = x[(x.MJD >= a) & (x.MJD < b)]
        if len(y) > 10:
            print(cam, f, lab, len(y), round(np.average(y.uJy, weights=1 / y.duJy ** 2), 2), round(1 / np.sqrt((1 / y.duJy ** 2).sum()), 2))
