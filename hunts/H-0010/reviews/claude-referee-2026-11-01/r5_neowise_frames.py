"""r5: exposure-level NEOWISE checks (H-0009 style) for the candidates with a NEOWISE visit during or near the Gaia event.
For each: per-visit table (nwlib.visit_table): the detection nearest the Gaia star within 3" and the summed flux of every
detection within 8" per frame; baseline = median of visits outside the event window; event-visit ratios from (a) every frame,
(b) clean frames only (cc 00, nb 1, unsaturated), (c) blend total within 8"; the share of frames with a detection near the star
(event vs quiet: a jump means the star is only extracted when bright, i.e. the baseline is not the star); centroid shift of the
event frames against the quiet centroid and the shift predicted if the Gaia star brightened (f_ex * (Gaia - quiet centroid)).
J174618 in detail: a 25" cone (cached), AllWISE and 2MASS within 15" (VizieR), and the star's W1 baseline under several definitions.
Writes data/neowise_ratios.csv. Run: uv run python -I hunts/H-0010/reviews/claude-referee-2026-11-01/r5_neowise_frames.py"""
import io, os, sys
import numpy as np, pandas as pd, requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nwlib  # noqa: E402

pd.set_option("display.width", 250)
C = pd.read_csv(os.path.join(HERE, "data", "candidates21.csv"), dtype={"source_id": str}).set_index("source_id")
# event windows (MJD) from the Gaia light curves; event visit = the NEOWISE visit inside it nearest the Gaia peak
EV = {"4067152339419332992": (57000, 57200), "5958944416543307648": (56700, 57150), "5620272814897694848": (56900, 57250),
      "2054828730840779520": (57250, 57480), "4096047127002546560": (57150, 57350), "4063479523864717184": (57560, 57760)}
out = []
for sid, (w0, w1) in EV.items():
    c = C.loc[sid]
    d = nwlib.load(os.path.join(HERE, "data", "frames", f"{sid}.csv"), c.ra, c.dec)
    vt = nwlib.visit_table(d)
    q = vt[(vt.mjd < w0) | (vt.mjd > w1)]
    print(f"\n=== {c['name']} ({sid}); quiet visits {len(q)}; event-window visits: {list(vt[(vt.mjd >= w0) & (vt.mjd <= w1)].mjd.round(1))}")
    print(vt.round(2).to_string(index=False))
    b1, b2 = q.W1_near.median(), q.W2_near.median()
    bt1, bt2 = q.W1_tot.median(), q.W2_tot.median()
    bc = q.W1_near_clean.median()
    rms1 = 1.4826 * np.median(np.abs(q.W1_near - b1))
    qd = d[d.vis.isin(q.vis)]
    qn = qd[qd.r < 3]
    cx, cy = qn.dx.median(), qn.dy.median()
    share_q = (qd[qd.r < 3].fk.nunique()) / max(qd.fk.nunique(), 1)
    for v in vt[(vt.mjd >= w0) & (vt.mjd <= w1)].itertuples():
        e = d[d.vis == v.vis]
        en = e[e.r < 3].sort_values("r").drop_duplicates("fk")
        share_e = en.fk.nunique() / max(e.fk.nunique(), 1)
        r1 = 10 ** (0.4 * (b1 - v.W1_near)); r2 = 10 ** (0.4 * (b2 - v.W2_near))
        rt1 = 10 ** (0.4 * (bt1 - v.W1_tot)); rt2 = 10 ** (0.4 * (bt2 - v.W2_tot))
        rc = 10 ** (0.4 * (bc - v.W1_near_clean)) if np.isfinite(v.W1_near_clean) else np.nan
        fex = 1 - 1 / r1
        pred = (fex * (0 - cx), fex * (0 - cy))
        sh = (v.dx_near - cx, v.dy_near - cy)
        sx = 1.4826 * np.median(np.abs(qn.dx - cx)) / np.sqrt(max(len(en), 1))
        sy = 1.4826 * np.median(np.abs(qn.dy - cy)) / np.sqrt(max(len(en), 1))
        scat_e = 1.4826 * np.median(np.abs(en.w1mpro - en.w1mpro.median())) if len(en) > 2 else np.nan
        scat_q = qn.groupby("vis").w1mpro.apply(lambda x: 1.4826 * np.median(np.abs(x - x.median())) if len(x) > 2 else np.nan).median()
        print(f"  visit {v.mjd:.1f}: W1 x{r1:.2f} W2 x{r2:.2f} (near-star, {v.n_near} frames, baseline W1 {b1:.2f} rms {rms1:.3f}); "
              f"clean-only W1 x{rc:.2f} ({v.n_near_clean} frames); blend total W1 x{rt1:.2f} W2 x{rt2:.2f}; "
              f"frames with a detection <3\": event {share_e:.2f} vs quiet {share_q:.2f}; det/frame event {v.det_per_frame} quiet {q.det_per_frame.median()}; "
              f"quiet centroid ({cx:+.2f},{cy:+.2f})\" event ({v.dx_near:+.2f},{v.dy_near:+.2f}); shift ({sh[0]:+.2f},{sh[1]:+.2f}) +- ({sx:.2f},{sy:.2f}) "
              f"vs predicted for the Gaia star ({pred[0]:+.2f},{pred[1]:+.2f}); frame scatter event {scat_e:.3f} quiet {scat_q:.3f}")
        out.append(dict(source_id=sid, name=c["name"], mjd=v.mjd, n=v.n_near, W1=r1, W2=r2, W1_clean=rc, W1_tot=rt1, W2_tot=rt2,
                        share_e=share_e, share_q=share_q, rms1=rms1))
pd.DataFrame(out).to_csv(os.path.join(HERE, "data", "neowise_ratios.csv"), index=False)

# ---- J174618 in detail
sid = "4067152339419332992"
c = C.loc[sid]
print("\n=== J174618 detail")
p = os.path.join(HERE, "data", "frames", f"{sid}_25as.csv")
if not os.path.exists(p):
    cols = "mjd,ra,dec,w1mpro,w1sigmpro,w2mpro,w2sigmpro,w1mag,nb,na,cc_flags,ph_qual,qual_frame,w1sat,w1rchi2,scan_id,frame_num,allwise_cntr,r_allwise"
    qq = f"SELECT {cols} FROM neowiser_p1bs_psd WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{c.ra},{c.dec},{25/3600}))=1"
    r = requests.post("https://irsa.ipac.caltech.edu/TAP/sync", data={"QUERY": qq, "FORMAT": "csv"}, timeout=1500)
    open(p, "w").write(r.text)
d = nwlib.load(p, c.ra, c.dec)
d["sx"], d["sy"] = d.dx.round(0), d.dy.round(0)
print("detections within 25\" grouped by 2\" cells, all visits (count, median W1, median position):")
d["cell"] = (d.dx / 2.5).round().astype(int).astype(str) + "," + (d.dy / 2.5).round().astype(int).astype(str)
g = d.groupby("cell").agg(n=("mjd", "size"), W1=("w1mpro", "median"), W2=("w2mpro", "median"), dx=("dx", "median"), dy=("dy", "median"),
                          nb=("nb", "median"), cntr=("allwise_cntr", lambda s: s.dropna().astype("int64").mode().iloc[0] if s.notna().any() else -1))
print(g[g.n >= 5].sort_values("n", ascending=False).round(2).to_string())
ev = d[(d.mjd > 57099) & (d.mjd < 57101)]
print("event visit (2015-03-19) detections within 25\":")
print(ev.groupby("cell").agg(n=("mjd", "size"), W1=("w1mpro", "median"), W2=("w2mpro", "median"), dx=("dx", "median"), dy=("dy", "median"),
                             nb=("nb", "median")).round(2).to_string())
for cat, lab in (("II/328/allwise", "AllWISE"), ("II/246/out", "2MASS")):
    try:
        q = requests.get("https://vizier.cds.unistra.fr/viz-bin/asu-tsv", params={"-source": cat, "-c": f"{c.ra} {c.dec}", "-c.rs": 15,
                         "-out": "**", "-out.add": "_r,_RAJ2000,_DEJ2000", "-out.max": 50}, timeout=120)
        lines = [ln for ln in q.text.splitlines() if ln and not ln.startswith("#")]
        t = pd.read_csv(io.StringIO("\n".join([lines[0]] + lines[3:])), sep="\t")
        t["dx"] = (t._RAJ2000.astype(float) - c.ra) * np.cos(np.radians(c.dec)) * 3600
        t["dy"] = (t._DEJ2000.astype(float) - c.dec) * 3600
        keep = [k for k in ("_r", "dx", "dy", "AllWISE", "W1mag", "W2mag", "W3mag", "ccf", "ex", "nb", "2MASS", "Jmag", "Hmag", "Kmag", "Qflg", "Cflg") if k in t]
        print(f"{lab} within 15\":"); print(t[keep].round(2).to_string(index=False))
    except Exception as e:  # noqa: BLE001
        print(lab, "UNKNOWN", e)
