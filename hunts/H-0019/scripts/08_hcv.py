"""Exploratory cross-check against the Hubble Catalog of Variables (Bonanos+2019), which used 5 or more visits of the
same photometry. For stars HCV examined in ACS F814W: does one first-last pair agree with HCV's verdict?

Writes work/hcv_check.csv.
"""
import io, csv, glob, pathlib
import httpx, numpy as np, pandas as pd

HERE = pathlib.Path(__file__).resolve().parents[1]
API = "https://catalogs.mast.stsci.edu/api/v0.1/hsc/v3/hcvsummary.csv"
probe = {}
for f in glob.glob(str(HERE / "work/probe*.csv")):
    for r in csv.DictReader(open(f)):
        probe[r["name"]] = r
rows = []
for f in sorted(glob.glob(str(HERE / "work/pairs/*.parquet"))):
    key = pathlib.Path(f).stem; name = key.replace("_", " ") if key.replace("_", " ") in probe else key
    p = pd.read_parquet(f); p = p[(p.kind == "long") & p.box.isin(["agb", "agb_bright", "rgb"])]
    if len(p) < 30 or name not in probe:
        continue
    g = probe[name]; frames = []
    for page in range(1, 40):
        try:
            t = httpx.get(API, params=dict(ra=g["ra"], dec=g["dec"], radius=g["radius"], Filter="ACS_F814W", pagesize=50000, page=page, sort_by="MatchID"), timeout=300).text
        except Exception as e:  # noqa: BLE001
            print(name, "error", repr(e)[:80]); break
        if not t.strip():
            break
        df = pd.read_csv(io.StringIO(t)); frames.append(df)
        if len(df) < 50000:
            break
    if not frames:
        print(name, "not in HCV (ACS_F814W)"); continue
    h = pd.concat(frames).drop_duplicates("MatchID")
    m = p.merge(h[["MatchID", "AutoClass", "ExpertClass", "NumLC", "MAD"]], on="MatchID")
    for box in ("agb", "agb_bright", "rgb"):
        s = m[m.box == box]
        if not len(s):
            continue
        big, var = s.d.abs() > 0.3, s.AutoClass >= 1
        rows.append(dict(name=name, box=box, n=len(s), hcv_var=int(var.sum()), big=int(big.sum()), both=int((big & var).sum()),
                         f_big_given_var=round(float((big & var).sum() / max(var.sum(), 1)), 3),
                         f_var_given_big=round(float((big & var).sum() / max(big.sum(), 1)), 3), med_numlc=float(s.NumLC.median())))
    print(name, "HCV rows", len(h), "matched", len(m), flush=True)
df = pd.DataFrame(rows); df.to_csv(HERE / "work/hcv_check.csv", index=False)
print(df.to_string(index=False))
