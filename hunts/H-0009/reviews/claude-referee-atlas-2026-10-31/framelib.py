"""Exposure-level NEOWISE diagnostics of one event (referee's own code). Input: the r0 download (every NEOWISE-R single exposure
within 6" of the AllWISE position) and the event row of sky4_strong / sky4_classified.

Frames of the star = detections with allwise_cntr == cntr (the association the survey used). Kept in W1 by the survey's relaxed
rule (neowise_lens.relaxed): qual_frame>0, qi_fact>0, saa_sep>0, moon_masked W1 '0', cc_flags W1 in {0,h,d}, ph_qual W1 A/B, nb<=3,
sso_flg==0. Each kept frame is classed: 'clean' (cc W1 and W2 '0', nb==1, not saturated), else flagged as hd / nb / sat.
Per event (peak visit = the visit at t; quiet visits = outside the block t_first..t_last):
  d_all     median W1 of the event-visit frames minus the median of the quiet-visit medians (all kept frames)
  d_clean   same, clean frames only, each against the clean-frame baseline (NaN if the event visit has < 2 clean frames)
  d_flag    same, flagged frames only
  R_ap      excess flux in the standard-aperture magnitude (w1mag) / excess flux in the profile fit (w1mpro). A real brightening
            of an isolated source gives ~1; a deblending error that moves flux between components gives ~0
  R_tot     excess of the summed W1 profile-fit flux of every detection in the same frame within 6" / excess of the star's flux.
            ~1 if the star really brightened, ~0 if flux moved from a neighbour component into the star
  shift     centroid offset (arcsec) of the event frames against the quiet-visit frames, and its significance
  frames    number of kept event frames against the median per quiet visit
  scat      robust frame scatter in the event visit / median quiet-visit frame scatter
"""
import numpy as np
import pandas as pd

GAP = 30.0
SAT_W1 = 8.0


def kept_w1(d):
    cc = d.cc_flags.astype(str).str.zfill(4)
    ph = d.ph_qual.astype(str)
    mm = d.moon_masked.astype(str).str.zfill(2)
    ok = ((d.qual_frame > 0) & (d.qi_fact > 0) & (d.saa_sep > 0) & (mm.str[0] == "0") & cc.str[0].isin(["0", "h", "d"])
          & ph.str[0].isin(["A", "B"]) & (d.nb <= 3) & (d.sso_flg.fillna(1) == 0) & np.isfinite(d.w1mpro))
    return ok.to_numpy()


def classify(d):
    cc = d.cc_flags.astype(str).str.zfill(4)
    hd = (cc.str[0] != "0") | (cc.str[1] != "0")
    nbx = d.nb > 1
    sat = (d.w1sat.fillna(1) >= 0.05) | (d.w1mpro <= SAT_W1)
    return hd.to_numpy(), nbx.to_numpy(), sat.to_numpy()


def visits(t):
    t = np.asarray(t)
    o = np.argsort(t)
    g = np.zeros(len(t), int)
    g[o] = np.concatenate([[0], np.cumsum(np.diff(t[o]) > GAP)])
    return g


def f(m):
    return 10 ** (-0.4 * np.asarray(m, float))


def analyse(fr, row):
    cntr = int(row.allwise_cntr)
    da = fr[(fr.allwise_cntr.astype("Int64") == cntr)].copy()
    if len(da) < 30:
        return None
    da["vis"] = visits(da.mjd.values)
    # the survey kept only detections within 2" of the AllWISE position (neowise_lens._read_release: r_allwise < 2)
    d = da[(da.r_allwise < 2.0).to_numpy() & kept_w1(da)].copy()
    if len(d) < 30:
        return None
    vt = d.groupby("vis").mjd.median()
    ev_vis = int((vt - row.t).abs().idxmin())
    if abs(vt[ev_vis] - row.t) > 3:
        return None
    blk = vt[(vt >= row.t_first - 3) & (vt <= row.t_last + 3)].index
    d["hd"], d["nbx"], d["sat"] = classify(d)
    d["clean"] = ~(d.hd | d.nbx | d.sat)
    q = d[~d.vis.isin(blk)]
    e = d[d.vis == ev_vis]
    if q.vis.nunique() < 4 or len(e) < 3:
        return None
    out = dict(cntr=cntr, n_ev=len(e), n_q_med=float(q.groupby("vis").size().median()))
    qv = q.groupby("vis").w1mpro.median()
    base = float(qv.median())
    out["d_all"] = float(e.w1mpro.median() - base)
    for lab, sel_e, sel_q in (("clean", e.clean, q.clean), ("flag", ~e.clean, ~q.clean)):
        ee, qq = e[sel_e.values], q[sel_q.values]
        if len(ee) >= 2 and qq.vis.nunique() >= 3:
            b = float(qq.groupby("vis").w1mpro.median().median())
            out[f"d_{lab}"] = float(ee.w1mpro.median() - b)
            s = 1.4826 * np.median(np.abs(ee.w1mpro - ee.w1mpro.median())) / np.sqrt(len(ee))
            out[f"d_{lab}_err"] = float(max(s, 0.01))
        else:
            out[f"d_{lab}"], out[f"d_{lab}_err"] = np.nan, np.nan
        out[f"n_ev_{lab}"] = int(len(ee))
    out["frac_clean_ev"] = float(e.clean.mean())
    # share of the star's associated detections that pass r_allwise < 2 (position wobble), event visit vs quiet visits
    ae, aq = da[da.vis == ev_vis], da[~da.vis.isin(blk)]
    out["pass_r2_ev"] = float((ae.r_allwise < 2).mean()) if len(ae) else np.nan
    out["pass_r2_q"] = float((aq.r_allwise < 2).mean()) if len(aq) else np.nan
    out["frac_hd_ev"], out["frac_nb_ev"], out["frac_sat_ev"] = float(e.hd.mean()), float(e.nbx.mean()), float(e.sat.mean())
    out["frac_hd_q"], out["frac_nb_q"], out["frac_sat_q"] = float(q.hd.mean()), float(q.nbx.mean()), float(q.sat.mean())
    # aperture vs profile fit (excess flux ratio)
    ex_psf = np.median(f(e.w1mpro)) - np.median(q.groupby("vis").w1mpro.median().map(lambda m: f(m)))
    if e.w1mag.notna().sum() >= 3 and q.w1mag.notna().sum() >= 10:
        ex_ap = np.nanmedian(f(e.w1mag)) - np.nanmedian(q.groupby("vis").w1mag.median().map(lambda m: f(m)))
        out["R_ap"] = float(ex_ap / ex_psf) if ex_psf > 0 else np.nan
    else:
        out["R_ap"] = np.nan
    # summed flux of every detection in the same frame within 6" (blend total)
    fr2 = fr[np.isfinite(fr.w1mpro)].copy()
    fr2["fk"] = fr2.scan_id.astype(str) + "_" + fr2.frame_num.astype(str)
    tot = fr2.groupby("fk").w1mpro.apply(lambda m: f(m).sum())
    nd = fr2.groupby("fk").size()
    d["fk"] = d.scan_id.astype(str) + "_" + d.frame_num.astype(str)
    d["tot"] = d.fk.map(tot)
    d["ndet"] = d.fk.map(nd)
    e, q = d[d.vis == ev_vis], d[~d.vis.isin(blk)]
    ex_tot = np.median(e.tot) - np.median(q.groupby("vis").tot.median())
    out["R_tot"] = float(ex_tot / ex_psf) if ex_psf > 0 else np.nan
    out["ndet_ev"], out["ndet_q"] = float(e.ndet.median()), float(q.ndet.median())
    out["frac_merged_ev"] = float(np.mean(e.ndet < q.ndet.median()))
    out["frac_merged_q"] = float(np.mean(q.ndet < q.ndet.median()))
    # centroid
    dec0 = np.radians(q.dec.median())
    dx = ((e.ra - q.ra.median()) * np.cos(dec0) * 3600).median()
    dy = ((e.dec - q.dec.median()) * 3600).median()
    sx = 1.4826 * np.median(np.abs((q.ra - q.ra.median()) * np.cos(dec0) * 3600 - 0)) / np.sqrt(len(e))
    sy = 1.4826 * np.median(np.abs((q.dec - q.dec.median()) * 3600)) / np.sqrt(len(e))
    out["ox"], out["oy"], out["sx"], out["sy"] = float(dx), float(dy), float(max(sx, 0.01)), float(max(sy, 0.01))
    out["ra0"], out["de0"] = float(q.ra.median()), float(q.dec.median())
    out["shift"] = float(np.hypot(dx, dy))
    out["shift_sig"] = float(np.hypot(dx / max(sx, 0.01), dy / max(sy, 0.01)))
    out["shift_pa"] = float(np.degrees(np.arctan2(dx, dy)) % 360)
    # frame scatter
    qs = q.groupby("vis").w1mpro.apply(lambda m: 1.4826 * np.median(np.abs(m - m.median()))).median()
    es = 1.4826 * np.median(np.abs(e.w1mpro - e.w1mpro.median()))
    out["scat"] = float(es / max(qs, 0.005))
    # first vs second half of the event visit (scan progression)
    eo = e.sort_values("mjd")
    h = len(eo) // 2
    out["halves"] = float(eo.w1mpro.iloc[:h].median() - eo.w1mpro.iloc[h:].median()) if h >= 2 else np.nan
    # share of event frames individually brighter than baseline by > 3 sigma (sigma = quiet frame scatter)
    out["frac_frames_bright"] = float(np.mean(e.w1mpro < base - 3 * max(qs, 0.02)))
    return out, d, ev_vis, blk
