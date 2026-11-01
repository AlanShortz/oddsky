"""e1: the DR4 ensemble sample. Run from the repo root:  uv run python -I hunts/H-0009/predictions/work/ensemble/e1_sample.py

Starts from the Gaia DR3 sweep (hunts/H-0009/work/gaia_dr3_sweep.csv, 118 deduplicated strong events) and keeps the 64 events
inside the DR4 epoch-photometry span (2014-07-25 .. 2020-01-20). Then:
  - the 3 events Gaia DR3 already confirmed (J172057, J180402, J180839) leave the blind sample and become the grader's test set;
  - the 11 events with no Gaia DR3 source within 4" are excluded (no star to test);
  - the remaining 50 are the sample. The tested source is the survey's matched Gaia DR3 star (`survey_source_id`), fixed here.
    For off-target events whose centroid shift points at a different Gaia source, that source is recorded as `alt_source_id`
    (graded and reported, never counted).
  - GOST field-of-view transits (hunts/H-0009/reviews/gaia-dr3-sweep-2026-10-31/data/gost_transits.csv, fetched 2026-10-31 at the
    AllWISE position) within +-30 d of the NEOWISE event visit are counted; fewer than 2 makes the event untestable by design.

Writes hunts/H-0009/predictions/dr4_ensemble_sample.csv (forecast columns are added by e4), work/ensemble/excluded.csv and
work/ensemble/gost_sample.csv (the transits used)."""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PRED = os.path.abspath(os.path.join(HERE, "..", ".."))
H9 = os.path.abspath(os.path.join(PRED, ".."))
SWEEP = os.path.join(H9, "reviews", "gaia-dr3-sweep-2026-10-31", "data")
DR4_T0, DR4_T1 = 56863.44, 58868.0
DR3_T1 = 57900.0
W = 30.0  # event window half-width (d), the pre-registered rule's

s = pd.read_csv(os.path.join(H9, "work", "gaia_dr3_sweep.csv"), dtype={"survey_source_id": str, "gaia_source_id": str})
ev = pd.read_csv(os.path.join(SWEEP, "events.csv"), dtype={"g_source_id": str, "allwise_cntr": str})
cn = pd.read_csv(os.path.join(SWEEP, "cones.csv"), dtype={"source_id": str, "allwise_cntr": str})
st = pd.read_csv(os.path.join(H9, "work", "sky4_strong.csv"), dtype={"allwise_cntr": str, "g_source_id": str})
gost = pd.read_csv(os.path.join(SWEEP, "gost_transits.csv"))

s = s.merge(ev[["designation", "allwise_cntr", "ra", "dec", "l", "b", "dw2", "t_first", "t_last"]], on="designation", how="left")
s = s.merge(st[["designation", "t_prev", "t_next", "block_dw1"]], on="designation", how="left")
x = s[s.in_dr4_span].copy()
assert len(x) == 64, len(x)

excluded, rows = [], []
CASES = {"J163539": "OS-0020", "J173150": "OS-0021", "J124517": "OS-0022", "J160706": "OS-0023", "J131026": "OS-0024",
         "J154239": "OS-0025", "J172057": "OS-0026", "J180402": "OS-0027", "J180839": "OS-0029"}
# Optical information already in hand (ATLAS referees of H-0008 and H-0009). Used for per-event scenario weights in e4 and to
# define the "blind core" (events with no optical information at all).
OPTICAL = {
    "J163539": "ATLAS: smooth achromatic x6-9 event peaking 2017 Aug 15-18 (H-0008 atlas10 referee, P(lens) 0.75)",
    "J173150": "ATLAS: x7.7 event peaking 2018 Jul 11-14, rise mildly chromatic (H-0008 atlas10 referee, P(lens) 0.55)",
    "J075219": "ATLAS: real month-long brightening 2018 Mar 7-Apr 5, x5-8, too sparse to classify (H-0008 atlas10 referee)",
    "J185846": "ATLAS: eruptive red IR source; the matched Gaia star (2.8\") is not the variable (H-0008 atlas10 referee)",
    "J182120": "ATLAS: IR variable (SIMBAD YSO candidate) that brightened again in 2021; not a lens (H-0008 atlas10 referee)",
    "J075928": "ATLAS frames around the event unusable (H-0008 atlas10 referee): no information",
    "J170153": "ATLAS: flat (x1.04 +- 0.04) at +9 and +21 d where a lens on the star needs ~x2: IR-only (H-0009 referee)",
    "J185035": "ATLAS: flat (x0.92); IR source far too red for the Gaia star: IR-only (H-0009 referee)",
    "J173349": "ATLAS: no frame within 45 d; OGLE observed the field in 2015 with no alert (H-0009 referee): unconstrained",
}
for r in x.itertuples():
    k = r.designation[:7]
    if r.n_epochs > 0:
        excluded.append(dict(designation=r.designation, reason="Gaia DR3 epoch photometry already shows the event (achromatic "
                             f"brightening, {r.G_30} in G); not blind. Used as the grader's test set", case=CASES.get(k, "")))
        continue
    if r.n_gaia_4as == 0:
        excluded.append(dict(designation=r.designation, reason="no Gaia DR3 source within 4\" of the AllWISE position: nothing to "
                             "test (DR4 might add a faint source; not counted)" + ("; off-target" if str(r.off_target) == "True" else ""),
                             case=CASES.get(k, "")))
        continue
    sid = r.survey_source_id
    assert isinstance(sid, str) and sid.isdigit(), (r.designation, sid)
    c = cn[(cn.allwise_cntr == r.allwise_cntr) & (cn.source_id == sid)]
    assert len(c) == 1, (r.designation, sid)
    c = c.iloc[0]
    alt = r.gaia_source_id if (r.gaia_source_id != sid and isinstance(r.gaia_source_id, str)) else ""
    altc = cn[(cn.allwise_cntr == r.allwise_cntr) & (cn.source_id == alt)] if alt else None
    g = np.sort(gost[gost.designation == r.designation].mjd.to_numpy())
    g = g[(g >= DR4_T0) & (g <= DR4_T1)]
    dt = g - r.t
    n30 = int((np.abs(dt) <= W).sum())
    near = np.sort(np.abs(dt))
    tp = r.t_prev if np.isfinite(r.t_prev) else r.t - 182.6
    tn = r.t_next if np.isfinite(r.t_next) else r.t + 182.6
    rows.append(dict(
        designation=r.designation, hunts=r.hunts, case=CASES.get(k, ""), ra=r.ra, dec=r.dec, l=round(r.l, 3), b=round(r.b, 3),
        t_event_mjd=r.t, event_date=r.date, dw1=r.dw1, abs_dw1=round(abs(r.dw1), 3), dw2=round(r.dw2, 3),
        neowise_ratio=r.neowise_ratio, nblock=int(r.nblock) if np.isfinite(r.nblock) else 1,
        t_first=r.t_first if np.isfinite(r.t_first) else r.t, t_last=r.t_last if np.isfinite(r.t_last) else r.t,
        t_prev=round(tp, 3), t_next=round(tn, 3), t_prev_assumed=not np.isfinite(r.t_prev),
        block_dw1=r.block_dw1 if isinstance(r.block_dw1, str) else f"[{r.dw1:.3f}]",
        source_id=sid, source_basis="survey match (brightest Gaia DR3 star within 3\" of the AllWISE source)",
        sep_arcsec=round(float(c.sep), 2), G=round(float(c.Gmag), 3) if np.isfinite(c.Gmag) else np.nan,
        BP=round(float(c.BPmag), 3) if np.isfinite(c.BPmag) else np.nan, RP=round(float(c.RPmag), 3) if np.isfinite(c.RPmag) else np.nan,
        bp_rp=round(float(c.BPRP), 3) if np.isfinite(c.BPRP) else np.nan, n_gaia_4as=int(r.n_gaia_4as),
        off_target=("" if pd.isna(r.off_target) else str(r.off_target)),
        alt_source_id=alt, alt_sep_arcsec=round(float(altc.sep.iloc[0]), 2) if alt else np.nan,
        alt_note=("centroid shift points at this source: " + (r.notes.split(";")[0] if isinstance(r.notes, str) else "")) if alt else "",
        centroid_note=(r.notes if (str(r.off_target) == "True" and isinstance(r.notes, str) and "explains" in r.notes) else ""),
        in_dr3_span=bool(r.t <= DR3_T1), dr3_var_flag=r.var_flag,
        gost_n_fov_30=n30, gost_nearest_d=round(float(near[0]), 1), gost_2nd_d=round(float(near[1]), 1),
        gost_times_30=";".join(f"{v:.3f}" for v in g[np.abs(dt) <= W]),
        status="testable" if n30 >= 2 else "untestable by design (GOST: fewer than 2 transits within +-30 d)",
        optical_info=OPTICAL.get(k, ""),
        blind_core=(k not in OPTICAL or k == "J075928") and n30 >= 2,
    ))
    gg = pd.DataFrame(dict(designation=r.designation, mjd=g))
    gg.to_csv(os.path.join(HERE, "gost_sample.csv"), mode="w" if len(rows) == 1 else "a", header=len(rows) == 1, index=False)

out = pd.DataFrame(rows)
assert out.source_id.str.fullmatch(r"\d{6,19}").all()
assert len(out) == 50 and len(excluded) == 14
out.to_csv(os.path.join(PRED, "dr4_ensemble_sample.csv"), index=False)
pd.DataFrame(excluded).to_csv(os.path.join(HERE, "excluded.csv"), index=False)
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 100)
print(f"{len(x)} events in the DR4 span; {len(excluded)} excluded; sample {len(out)}; testable {int((out.status == 'testable').sum())}; "
      f"blind core {int(out.blind_core.sum())}\n")
print(pd.DataFrame(excluded).to_string(index=False), "\n")
print(out[["designation", "case", "event_date", "abs_dw1", "nblock", "source_id", "sep_arcsec", "G", "bp_rp", "off_target",
           "alt_source_id", "in_dr3_span", "gost_n_fov_30", "gost_nearest_d", "status", "blind_core"]].to_string(index=False))
