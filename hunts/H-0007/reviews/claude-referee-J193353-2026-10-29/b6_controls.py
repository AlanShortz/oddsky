"""b6: controls in the same frames. 20' cone, event visit vs the adjacent visits (2019 Oct, 2020 Sep). Match detections into
sources (AllWISE cntr where associated, else 2" positional groups), compute per-source visit medians and the event-minus-adjacent change.
Also per scan: target vs magnitude-matched controls in exactly the same scan/frame. Outside the Oddsky tools (pandas)."""
import numpy as np
import pandas as pd

pd.set_option("display.width", 250)
RA, DEC = 293.471115, -21.3037472
TC = 2938021301351037214
w = pd.read_parquet("/tmp/j1933ref/wide.parquet")
w["allwise_cntr"] = w.allwise_cntr.fillna(0).astype("int64")
w["sep"] = 3600 * np.hypot((w.ra - RA) * np.cos(np.radians(DEC)), w.dec - DEC)
w["cc"] = w.cc_flags.astype(str).str.zfill(4)
good = (w.allwise_cntr > 0) & (w.nb == 1) & (w.cc == "0000") & (w.qual_frame > 0)
print("rows", len(w), "good-associated", good.sum())
a = w[good & (w.r_allwise < 2.0)]
s = a.groupby(["allwise_cntr", "lab"]).agg(w1=("w1mpro", "median"), w2=("w2mpro", "median"), n=("mjd", "size"), sep=("sep", "median")).unstack("lab")
s = s.dropna()
s = s[(s["n"]["ev"] >= 5) & (s["n"]["pre"] >= 5) & (s["n"]["post"] >= 5)]
ref1 = (s["w1"]["pre"] + s["w1"]["post"]) / 2
ref2 = (s["w2"]["pre"] + s["w2"]["post"]) / 2
d = pd.DataFrame({"w1ref": ref1, "dw1": s["w1"]["ev"] - ref1, "dw2": s["w2"]["ev"] - ref2, "pp": s["w1"]["post"] - s["w1"]["pre"], "sep": s["sep"]["ev"]})
print("sources measured in all three visits:", len(d))
d["bin"] = pd.cut(d.w1ref, [5, 9, 11, 12, 12.6, 13.6, 14.0, 14.5])
print(d.groupby("bin", observed=True).agg(n=("dw1", "size"), med_dw1=("dw1", "median"), mad_dw1=("dw1", lambda x: 1.4826 * np.median(np.abs(x - np.median(x)))),
                                          med_dw2=("dw2", "median"), n_gt03=("dw1", lambda x: (x < -0.3).sum())).round(3).to_string())
print("target:", d.drop(columns="bin").loc[TC].round(3).to_dict() if TC in d.index else "missing")
print("\nall sources with dW1 < -0.3 (and W1ref < 14.5):")
print(d[(d.dw1 < -0.3)].drop(columns="bin").sort_values("dw1").round(3).to_string())
m = d[(d.w1ref > 12.6) & (d.w1ref < 13.6)]
print(f"\nW1 12.6-13.6 controls: n={len(m)}; dW1 median {m.dw1.median():+.3f} MAD {1.4826*np.median(np.abs(m.dw1-m.dw1.median())):.3f}; "
      f"rank of target: {(m.dw1 < d.loc[TC, 'dw1']).sum()} sources more negative")
# per scan / frame: target minus median of controls (W1 12.5-13.6 within 20') in the same frame, relative to each control's adjacent-visit level
ev = w[(w.lab == "ev") & good & (w.r_allwise < 2.0)].copy()
ev["ref"] = ev.allwise_cntr.map(ref1)
ev["dd"] = ev.w1mpro - ev.ref
fr = ev[(ev.ref > 12.5) & (ev.ref < 13.6) & (ev.allwise_cntr != TC)].groupby(["scan_id", "frame_num"]).agg(n=("dd", "size"), ctrl=("dd", "median"))
tg = w[(w.lab == "ev") & (w.sep < 2.5)].set_index(["scan_id", "frame_num"])[["mjd", "w1mpro", "w2mpro", "nb", "qual_frame", "moon_masked", "w1rchi2"]]
tg["dw1"] = tg.w1mpro - ref1.get(TC, np.nan)
print("\nper frame: target dW1 vs control median dW1 (W1 12.5-13.6, same frame)")
print(tg.join(fr).sort_values("mjd").round(3).to_string())
# bright stars within 1 deg
b = pd.read_parquet("/tmp/j1933ref/bright1deg.parquet")
b["sep"] = np.hypot((b.ra - RA) * np.cos(np.radians(DEC)), b.dec - DEC) * 60
bb = b.groupby("allwise_cntr").agg(ra=("ra", "median"), dec=("dec", "median"), w1=("w1mpro", "median"), sep_arcmin=("sep", "median"), n=("mjd", "size"))
print("\nbright (W1 < 7.5) sources within 1 deg in the event visit:", len(bb), "; W1 < 6:")
print(bb[bb.w1 < 6].sort_values("sep_arcmin").round(2).to_string())
# cc_flags of anything within 60" of the target in the event visit
nb = w[(w.lab == "ev") & (w.sep < 60)]
print("\nwithin 60\" in event visit: cc_flags counts", nb.cc.value_counts().to_dict(), "; nb>1 rows", (nb.nb > 1).sum())
print(nb[nb.cc != "0000"][["mjd", "sep", "w1mpro", "w2mpro", "cc", "nb", "scan_id"]].round(2).to_string())
