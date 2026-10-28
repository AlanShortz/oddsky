import sys, numpy as np, pandas as pd
from astropy.io import ascii as aascii
f, ra0, dec0, tsplit, tbad = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
tbad = [float(x) for x in tbad.split(",")] if tbad != "none" else []
d = aascii.read(f, format="ipac").to_pandas()
d = d[(d.qual_frame > 0) & (d.qi_fact > 0) & (d.saa_sep > 0) & (d.moon_masked.astype(str).str.zfill(2) == "00")]
d = d[d.allwise_cntr > 0]
d["sep"] = np.hypot((d.ra - ra0) * np.cos(np.radians(dec0)), d.dec - dec0) * 3600
d["visit"] = (d.mjd.sort_values().diff() > 30).cumsum().reindex(d.index)
d = d.sort_values("mjd"); d["visit"] = (d.mjd.diff() > 30).cumsum()
vt = d.groupby("visit").mjd.median()
print("visits:", len(vt))
rows = []
for b, i in [("w1", 0), ("w2", 1)]:
    q = d[(d.cc_flags.astype(str).str.zfill(4).str[i] == "0") & (d.ph_qual.astype(str).str[i].isin(["A", "B"])) & (d.nb == 1) & (d[f"{b}snr"] >= 4)]
    q = q[np.isfinite(q[f"{b}mpro"].astype(float))]
    v = q.groupby(["allwise_cntr", "visit"]).agg(m=(f"{b}mpro", "median"), n=(f"{b}mpro", "size"), sep=("sep", "median")).reset_index()
    v = v[v.n >= 3]
    v["t"] = v.visit.map(vt)
    for t in tbad:
        v = v[(v.t - t).abs() > 20]
    pre = v[v.t < tsplit].groupby("allwise_cntr").agg(pre=("m", "median"), npre=("m", "size"), sep=("sep", "median"))
    post = v[v.t > tsplit].groupby("allwise_cntr").agg(post=("m", "median"), npost=("m", "size"))
    s = pre.join(post, how="inner"); s = s[(s.npre >= 4) & (s.npost >= 6)]
    s["d"] = s.post - s.pre; s["band"] = b
    rows.append(s)
    # per-visit field offsets (mag - source median), for sources 9.5-12.5
    v2 = v.merge(s[["pre"]], left_on="allwise_cntr", right_index=True)
    v2 = v2[(v2.pre > 9.5) & (v2.pre < 12.5)]
    v2["off"] = v2.m - v2.groupby("allwise_cntr").m.transform("median")
    zp = v2.groupby("t").off.agg(["median", "size"])
    print(b, "per-visit field offset (stars 9.5-12.5 mag):"); print(zp.round(3).T.to_string())
S = pd.concat(rows).reset_index()
P = S.pivot_table(index="allwise_cntr", columns="band", values=["pre", "d", "sep"])
P.columns = [f"{a}_{b}" for a, b in P.columns]
P = P.dropna()
P.to_csv(f + ".steps.csv")
tgt = P.sep_w1.idxmin()
print("target", tgt, P.loc[tgt].round(3).to_dict())
for lo, hi in [(9.5, 12.5), (10.5, 11.7)]:
    sel = P[(P.pre_w2 > lo) & (P.pre_w2 < hi) & (P.index != tgt)]
    print(f"\ncomparison stars W2 {lo}-{hi}: n={len(sel)}")
    for c in ["d_w1", "d_w2"]:
        x = sel[c]; mad = 1.4826 * np.median(np.abs(x - x.median()))
        print(c, "median", round(x.median(), 4), "robust std", round(mad, 4), "min", round(x.min(), 3), "n with d<-0.1:", int((x < -0.1).sum()))
    sel = sel.assign(dc=sel.d_w1 - sel.d_w2)
    print("d(W1-W2) median", round(sel.dc.median(), 4), "robust std", round(1.4826 * np.median(np.abs(sel.dc - sel.dc.median())), 4), "max", round(sel.dc.max(), 3))
allc = P[P.index != tgt]
print("\nall stars n=", len(allc), "; stars with d_w2 < -0.15:"); print(allc[allc.d_w2 < -0.15].round(3).to_string())
print("\nnearest 10 sources:"); print(P.sort_values("sep_w1").head(10).round(3).to_string())
