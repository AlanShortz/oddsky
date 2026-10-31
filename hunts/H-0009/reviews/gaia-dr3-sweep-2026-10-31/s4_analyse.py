"""s4: one row per deduplicated strong event: which Gaia DR3 source, what the DR3 variability tables say about every source within
4", and what the DR3 epoch photometry shows at the NEOWISE time. Writes hunts/H-0009/work/gaia_dr3_sweep.csv.

Source choice, in order: (1) a source within 4" whose epoch photometry brightens >= 5 sigma within +-90 d of the event; (2) for
events the H-0009 referee flagged off-target, the Gaia source whose position best explains the NEOWISE event-centroid shift
(predicted shift = f_ex x (source - quiet centroid), f_ex = excess share of the event flux; same test as r9_bulk); (3) the survey's
matched star; (4) the nearest source.

Epoch photometry: transits rejected by the photometric processing are dropped; Gaia's variability-outlier rejections are kept
(during a lens peak they are the peak). Baseline = median flux of transits more than 150 d from the event (all transits if < 10).
Flux ratios at the transit(s) nearest the event within +-30 d and the largest within +-90 d; error = per-transit error (+) the
baseline's robust scatter. Transits 0.07-1.5 d apart (the two fields of view, consecutive scans) are averaged into one epoch."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, DR3_T0, DR3_T1, EPOCH, H9, cones, events, mjd2date  # noqa: E402

DR4_T1 = 58868.0  # DR4 epoch photometry ends 2020-01-20
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 60)
pd.set_option("display.max_colwidth", 80)

ev = events()
cn = cones()
vs = pd.read_csv(os.path.join(DATA, "vari_varisum.csv"), dtype=str)
vc = pd.read_csv(os.path.join(DATA, "vari_vclassre.csv"), dtype=str)
vm = pd.read_csv(os.path.join(DATA, "vari_vmicro.csv"), dtype=str)
vc["ClassSc"] = vc.ClassSc.astype(float)
vc = vc.drop_duplicates(["source_id", "Classifier"]).rename(columns={"Class": "best_class_name", "ClassSc": "best_class_score"})
gost = pd.read_csv(os.path.join(DATA, "gost_transits.csv"))
assert set(vs.source_id) == set(cn.source_id[cn.VarFlag == "VARIABLE"]), "varisum and VarFlag disagree"
assert set(cn.source_id[cn.EpochPh == 1]) == set(cn.source_id[cn.VarFlag == "VARIABLE"])
cls = {r.source_id: f"{r.best_class_name} {r.best_class_score:.2f}" for r in vc.itertuples()}
inml = set(vm.source_id) | set(vs.source_id[vs.Vmicro.astype(str).isin(["1", "True", "true"])])


def ratios(df, band, t):
    d = df[(df.band == band) & (df.flag != "rejected_by_photometry") & np.isfinite(df.mag)].sort_values("t_mjd").copy()
    if len(d) < 5:
        return None
    base = d[np.abs(d.t_mjd - t) > 150]
    if len(base) < 10:
        base = d
    m0 = base.mag.median()
    d["f"] = 10 ** (-0.4 * (d.mag - m0))
    d["fe"] = d.f * 0.921 * d.err
    fb = 10 ** (-0.4 * (base.mag - m0))
    scat = 1.4826 * np.median(np.abs(fb - np.median(fb)))
    d["grp"] = (d.t_mjd.diff().fillna(99) > 1.5).cumsum()
    g = d.groupby("grp").agg(t=("t_mjd", "mean"), f=("f", "mean"), fe=("fe", lambda x: np.sqrt((x ** 2).sum()) / len(x)),
                             n=("f", "size"), dmag=("mag", lambda x: x.mean() - m0)).reset_index(drop=True)
    g["err"] = np.hypot(g.fe, scat)
    g["dt"] = g.t - t
    return dict(ep=g, med=m0, scat=scat, n=len(d))


def at(r, w):
    """Nearest epoch within +-w d and largest-excess epoch within +-w d."""
    if r is None:
        return None, None
    g = r["ep"][np.abs(r["ep"].dt) <= w]
    if g.empty:
        return None, None
    return g.loc[g.dt.abs().idxmin()], g.loc[g.f.idxmax()]


def fmt(x):
    return "" if x is None else f"{x['f']:.2f}+-{x['err']:.2f}@{x['dt']:+.0f}d"


def centroid_pick(e, c):
    """Gaia source that best explains the event-centroid shift; returns (source_id, miss arcsec, miss sigma, implied offset)."""
    if not np.isfinite(e.get("ox", np.nan)) or c.empty:
        return None, np.nan, np.nan, np.nan
    rW = 10 ** (-0.4 * e.d_all)
    fex = (rW - 1) / rW if rW > 1 else 0.0
    cosd = np.cos(np.radians(e.de0))
    gx = (c.RA_ICRS - e.ra0) * cosd * 3600
    gy = (c.DE_ICRS - e.de0) * 3600
    miss = np.hypot(e.ox - fex * gx, e.oy - fex * gy)
    sig = np.hypot((e.ox - fex * gx) / e.sx, (e.oy - fex * gy) / e.sy)
    i = int(np.argmin(miss.values))
    # implied position of the brightening source relative to the AllWISE position
    ix = e.ox / fex + (e.ra0 - e.ra) * cosd * 3600 if fex > 0 else np.nan
    iy = e.oy / fex + (e.de0 - e.dec) * 3600 if fex > 0 else np.nan
    return c.source_id.iloc[i], float(miss.iloc[i]), float(sig.iloc[i]), float(np.hypot(ix, iy))


rows, details = [], []
for e in (pd.Series(x) for x in ev.to_dict("records")):
    c = cn[cn.allwise_cntr == e["allwise_cntr"]].reset_index(drop=True)
    t = e["t"]
    in3 = DR3_T0 <= t <= DR3_T1
    in4 = DR3_T0 <= t <= DR4_T1
    gt = gost[gost.designation == e["designation"]]
    n30 = int((np.abs(gt.mjd - t) <= 30).sum())
    n90 = int((np.abs(gt.mjd - t) <= 90).sum())
    notes = []
    # epoch photometry for every source within 4"
    ep = {}
    for sid in c.source_id:
        p = os.path.join(EPOCH, f"{sid}.csv")
        if os.path.exists(p):
            ep[sid] = pd.read_csv(p)
    bright = []
    for sid, df in ep.items():
        rg = ratios(df, "G", t)
        _, mx = at(rg, 90)
        if mx is not None and (mx.f - 1) / mx.err >= 5 and mx.f > 1.1:
            bright.append((mx.f, sid))
    cp, cmiss, csig, coff = centroid_pick(e, c)
    if bright:
        sid, basis = max(bright)[1], "epoch photometry brightens"
    elif e.get("off_target") is True or str(e.get("off_target")) == "True":
        sid, basis = cp, "centroid shift (off-target)"
    elif isinstance(e["g_source_id"], str) and e["g_source_id"] in set(c.source_id):
        sid, basis = e["g_source_id"], "survey match"
    elif len(c):
        sid, basis = c.source_id.iloc[0], "nearest"
    else:
        sid, basis = None, "no Gaia DR3 source within 4\""
    if sid is not None and cp is not None and sid != cp and basis != "centroid shift (off-target)":
        notes.append(f"centroid shift prefers {cp} (miss {cmiss:.2f}\")")
    if basis == "centroid shift (off-target)" and cp is not None and cmiss > 0.3 and csig > 5:
        notes.append(f"no Gaia source within 4\" explains the centroid shift (best miss {cmiss:.2f}\", {csig:.0f} sigma; implied source "
                     f"{coff:.1f}\" from the AllWISE position)")
    row = dict(designation=e["designation"], hunts=e["hunts"], t=round(t, 3), date=mjd2date(t), dw1=round(e["dw1"], 3),
               neowise_ratio=round(10 ** (-0.4 * e["dw1"]), 2),
               nblock=e.get("nblock"), in_dr3_span=in3, in_dr4_span=in4, off_target=e.get("off_target"), n_gaia_4as=len(c),
               n_variable_4as=int((c.VarFlag == "VARIABLE").sum()), survey_source_id=e["g_source_id"] if isinstance(e["g_source_id"], str) else "",
               gaia_source_id=sid or "", choice=basis, sep=np.nan, G=np.nan, bp_rp=np.nan, var_flag="",
               classifier="", in_vari_microlensing=False, n_epochs=0, gost_n30=n30, gost_n90=n90,
               G_30="", BP_30="", RP_30="", G_90max="", dBP_minus_dRP="", dG_minus_dRP="", n_repeat=0, verdict="", notes="")
    if sid is not None:
        s = c[c.source_id == sid].iloc[0]
        row.update(sep=round(s.sep, 2), G=round(s.Gmag, 2), bp_rp=round(s.BPRP, 2) if np.isfinite(s.BPRP) else np.nan,
                   var_flag=s.VarFlag, classifier=cls.get(sid, ""), in_vari_microlensing=sid in inml)
    others = [f"{x} {cls[x]}" for x in c.source_id if x in cls and x != sid]
    if others:
        notes.append("classifier on another source within 4\": " + "; ".join(others))
    if any(x in inml for x in c.source_id if x != sid):
        notes.append("another source within 4\" is in vari_microlensing")
    # verdict
    df = ep.get(sid) if sid else None
    if df is not None:
        rg, rb, rr = (ratios(df, b, t) for b in ("G", "BP", "RP"))
        row["n_epochs"] = rg["n"] if rg else 0
        n3, _ = at(rg, 30)
        _, m9 = at(rg, 90)
        row["G_30"] = fmt(n3)
        row["G_90max"] = fmt(m9)
        for b, rx in (("BP", rb), ("RP", rr)):
            x, _ = at(rx, 30)
            row[f"{b}_30"] = fmt(x)
        # colour test at every epoch within +-90 d with a >= 5 sigma G excess
        ex = rg["ep"][(np.abs(rg["ep"].dt) <= 90) & ((rg["ep"].f - 1) / rg["ep"].err >= 5)] if rg else pd.DataFrame()
        diffs = []
        for x in ex.itertuples():
            b = rb["ep"].loc[(rb["ep"].t - x.t).abs().idxmin()] if rb else None
            q = rr["ep"].loc[(rr["ep"].t - x.t).abs().idxmin()] if rr else None
            if b is None or q is None or abs(b.t - x.t) > 0.5 or abs(q.t - x.t) > 0.5:
                continue
            eb = 1.0857 * b.err / max(b.f, 0.05)
            eq = 1.0857 * q.err / max(q.f, 0.05)
            diffs.append((b.dmag - q.dmag, np.hypot(eb, eq), x.dt, x.dmag, b.dmag, q.dmag))
        bp_faint = rb is None or rb["med"] > 20.5
        if diffs:
            w = np.array([1 / d[1] ** 2 for d in diffs])
            dd = float(np.sum(w * np.array([d[0] for d in diffs])) / w.sum())
            de = float(1 / np.sqrt(w.sum()))
            row["dBP_minus_dRP"] = f"{dd:+.2f}+-{de:.2f}" if not bp_faint else "BP too faint"
            row["dG_minus_dRP"] = f"{np.mean([d[3] - d[5] for d in diffs]):+.3f}"
            details.append((e["designation"], sid, diffs))
        # repeats: other epochs > 150 d away brightening by >= half the event excess and >= 5 sigma
        rep = pd.DataFrame()
        if rg and m9 is not None:
            o = rg["ep"][np.abs(rg["ep"].dt) > 150]
            rep = o[((o.f - 1) >= max(0.5 * (m9.f - 1), 0.1)) & ((o.f - 1) / o.err >= 5)]
            row["n_repeat"] = len(rep)
            if len(rep):
                notes.append("repeat brightenings: " + ", ".join(f"{mjd2date(x.t)} x{x.f:.2f}" for x in rep.itertuples()))
            oo = rg["ep"][np.abs(rg["ep"].dt) > 150]
            notes.append(f"G baseline {rg['med']:.2f}, scatter {rg['scat']:.3f} (flux), max outside +-150 d x{oo.f.max():.2f}")
        if n3 is None and m9 is None:
            row["verdict"] = "untested: epoch photometry but no Gaia transit within +-90 d"
        elif m9 is not None and (m9.f - 1) / m9.err >= 5 and m9.f > 1.1:
            chrom = False
            if diffs and not bp_faint:
                chrom = abs(dd) > max(3 * de, 0.1)
            elif diffs:
                notes.append("BP too faint (median > 20.5) for the colour test; G and RP compared")
                gr = [d[3] - d[5] for d in diffs]
                chrom = abs(np.mean(gr)) > 0.15
            if chrom or len(rep):
                row["verdict"] = "Gaia: chromatic or repeating variable (not a lens)"
            else:
                row["verdict"] = "Gaia-confirmed achromatic brightening (lens candidate)"
        elif n3 is not None:
            exp = 10 ** (-0.4 * e["dw1"])
            row["verdict"] = "Gaia flat at the NEOWISE time (no optical counterpart on that source)"
            notes.append(f"NEOWISE x{exp:.2f}; Gaia nearest x{n3.f:.2f}")
        else:
            row["verdict"] = "inconclusive: nearest Gaia transit 30-90 d away and flat"
    elif not in3:
        if in4:
            row["verdict"] = "outside the DR3 span: waits for DR4"
        elif t > DR4_T1:
            row["verdict"] = "after the DR4 span: waits for DR5"
        else:
            row["verdict"] = "before Gaia epoch photometry"
    else:
        if len(c) == 0:
            row["verdict"] = "no Gaia epoch photometry (untested): no Gaia DR3 source within 4\""
        else:
            row["verdict"] = "no Gaia epoch photometry (untested): no source within 4\" flagged VARIABLE"
            notes.append(f"GOST: {n30} predicted Gaia transits within +-30 d")
    if e.get("t_h8") is not None and np.isfinite(e.get("t_h8", np.nan)) and abs(e["t_h8"] - t) > 1:
        notes.append(f"H-0008 event visit {mjd2date(e['t_h8'])} (also outside DR3)" if not (DR3_T0 <= e["t_h8"] <= DR3_T1)
                     else f"H-0008 event visit {mjd2date(e['t_h8'])}")
    row["notes"] = "; ".join(notes)
    rows.append(row)

out = pd.DataFrame(rows)
assert out.gaia_source_id.astype(str).str.fullmatch(r"\d*").all()
out.to_csv(os.path.join(H9, "work", "gaia_dr3_sweep.csv"), index=False)
print(f"{len(out)} events -> work/gaia_dr3_sweep.csv\n")
print(out.verdict.value_counts().to_string(), "\n")
print("in the DR3 span:", out.in_dr3_span.sum())
print(out[out.in_dr3_span].groupby("verdict").size().to_string(), "\n")
cols = ["designation", "date", "dw1", "gaia_source_id", "choice", "sep", "G", "classifier", "in_vari_microlensing", "n_epochs",
        "gost_n30", "G_30", "BP_30", "RP_30", "G_90max", "dBP_minus_dRP", "n_repeat"]
print(out[out.n_epochs > 0][cols].to_string(index=False), "\n")
for d, sid, diffs in details:
    print(d, sid, "colour test per epoch (dBP-dRP, err, dt, dG, dBP, dRP):")
    for x in diffs:
        print("   " + "  ".join(f"{v:+.3f}" for v in x))
print()
print("MICROLENSING in the DR3 classifier (any source within 4\"):")
for r in vc[vc.best_class_name == "MICROLENSING"].itertuples():
    m = cn[cn.source_id == r.source_id]
    print(f"  {r.source_id} score {r.best_class_score:.2f}: " + ", ".join(f"{x.designation} ({x.sep:.2f}\")" for x in m.itertuples()))
print("\nevery classifier result:\n" + vc[["designation", "source_id", "Classifier", "best_class_name", "best_class_score"]].to_string(index=False))
print("vari_microlensing rows:", len(vm))
print("\nin-span events without epoch photometry:")
print(out[out.in_dr3_span & (out.n_epochs == 0)][["designation", "date", "dw1", "n_gaia_4as", "gaia_source_id", "choice", "sep", "G",
                                                  "var_flag", "gost_n30", "notes"]].to_string(index=False))
print("\noff-target events (re-association):")
print(out[out.off_target.astype(str) == "True"][["designation", "date", "survey_source_id", "gaia_source_id", "sep", "G", "notes"]].to_string(index=False))
