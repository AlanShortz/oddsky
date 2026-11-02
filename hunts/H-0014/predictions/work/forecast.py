"""Build the sealed sample (dr4_search_sample.csv) and the forecast numbers (work/forecast.json) for
hunts/H-0014/predictions/dr4_search_forecast.md. Run from the repo root:

    uv run python -I hunts/H-0014/predictions/work/forecast.py > hunts/H-0014/predictions/work/forecast.log

Inputs are committed files only (H-0010's vetted list, the H-0010 referee and ATLAS verdicts as transcribed below, the H-0009
ensemble sample, H-0014's target list and the DR3 dry run's epoch status). The Monte Carlos are the grader's `model_*`.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PRED = HERE.parent
ROOT = PRED.parents[2]
spec = importlib.util.spec_from_file_location("dr4_search_grade", PRED / "dr4_search_grade.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)

DR3_END = 57901.0
DR4_LO, DR4_HI = G.RELEASES["dr4"]["span"]

# P(lens) for H-0010's 21 first-pass candidates after the referee (reviews/claude-referee-2026-11-01.md, table) and the ATLAS
# follow-up (reviews/atlas-2026-11-01.md: J200958 0.45, J184922 0.10, J182811 0.25). Keyed by the first 7 characters.
P_REFEREE = {"J174618": 0.75, "J173332": 0.75, "J072830": 0.60, "J144905": 0.45, "J200958": 0.45, "J174656": 0.45,
             "J171847": 0.35, "J184922": 0.10, "J172020": 0.20, "J182124": 0.60, "J175414": 0.40, "J174036": 0.30,
             "J174029": 0.30, "J171234": 0.30, "J182656": 0.30, "J190032": 0.25, "J151331": 0.45, "J171838": 0.40,
             "J182811": 0.25, "J180313": 0.10, "J184837": 0.30}
# Events whose DR3 brightening rests on few scan dates (referee): more likely not to be reproduced by DR4's reprocessing.
TWO_DATES = {"J175414", "J182656", "J182811"}
SINGLE_FOV = {"J190032": 0.35}      # two single transits, both FOV2, never confirmed by the other field of view
ARTIFACTS = {"508920918409038464", "5939477464424988544"}
# P(lens) of Oddsky cases, from each case file (cases/OS-*/case.yaml): OS-0026 H1 0.65, OS-0027 H1 0.60, OS-0029 H1
# confidence 0.5; OS-0016 "P(not microlensing) = 0.05"; OS-0020 H1 0.75; OS-0021 H1 0.55.
CASE_P = {"5959812622743175552": 0.65, "4143495279954502016": 0.60, "4145977633638478336": 0.50}
CASE_P_F4 = {"J040025": ("OS-0016", 0.95), "J163539": ("OS-0020", 0.75), "J173150": ("OS-0021", 0.55)}


def f1_rows() -> pd.DataFrame:
    u = pd.read_csv(ROOT / "hunts/H-0010/work/gaia_ml_unpub.csv", dtype={"source_id": str})
    rows = []
    for r in u.itertuples():
        grp = {"known lens": "known lens", "Oddsky case": "Oddsky case", "new lens candidate": "first-pass candidate",
               "inconclusive": "inconclusive", "not a lens": "not a lens"}[r.verdict]
        p = P_REFEREE.get(r.name[:7], float(r.p_lens)) if grp == "first-pass candidate" else float(r.p_lens)
        p = CASE_P.get(r.source_id, p)
        gmag = float(r.phot_g_mean_mag)
        tp = float(r.t_peak) if pd.notna(r.t_peak) else np.nan
        excl = str(r.dr3_exclusion) if pd.notna(r.dr3_exclusion) else ""
        m, why = 1.0, []
        if grp == "known lens":
            m *= 1.15
            why.append("in a survey list x1.15")
        if gmag > 19:
            m *= 0.7
            why.append("G > 19 x0.7")
        if np.isfinite(tp) and tp >= DR3_END - 120:
            m *= 1.3
            why.append("DR3 peak within 120 d of DR3's end x1.3")
        if excl.startswith("OGLE tE"):
            m *= 0.6
            why.append("OGLE tE <= 20 d x0.6")
        if "binary lens" in excl:
            m = 0.6
            why = ["binary lens with caustic crossings (Gaia16aye): 0.6"]
        fm = 0.25 if r.source_id in ARTIFACTS else (1.0 if grp == "not a lens" else 2.0)
        case = {"5959812622743175552": "OS-0026", "4143495279954502016": "OS-0027",
                "4145977633638478336": "OS-0029"}.get(r.source_id, "")
        rows.append(dict(forecast="F1", key=r.name, source_id=r.source_id, alt_source_id="", ra=r.ra, dec=r.dec, group=grp,
                         case=case, G=round(gmag, 2), t_peak_dr3=tp, p_lens=p, cat_mult=round(m, 4), f_mult=fm,
                         f2_member=grp != "known lens", notes="; ".join(why)))
    return pd.DataFrame(rows)


def f3_rows(u: pd.DataFrame) -> pd.DataFrame:
    full = pd.read_csv(ROOT / "hunts/H-0010/work/gaia_ml_unpub.csv", dtype={"source_id": str}).set_index("source_id")
    c = u[u.group == "first-pass candidate"]
    rows = []
    for r in c.itertuples():
        f = full.loc[r.source_id]
        nw_ok = str(f.nw_status) == "ok"
        ztf_ok = str(f.ztf_status) == "ok"
        faint = r.G > 19
        pnr = SINGLE_FOV.get(r.key[:7], (0.05 if faint else 0.02) + (0.08 if r.key[:7] in TWO_DATES else 0.0))
        mult = (0.75 if nw_ok else 1.0) * (0.4 if ztf_ok else 1.0)
        rows.append(dict(forecast="F3", key=r.key, source_id=r.source_id, alt_source_id="", ra=r.ra, dec=r.dec,
                         group=r.group, G=r.G, t_peak_dr3=r.t_peak_dr3, p_lens=r.p_lens, r_lens=0.04 if faint else 0.02,
                         r_nonlens_mult=mult, p_norepro=pnr,
                         notes=f"NEOWISE repeat check {'yes' if nw_ok else 'no'}; ZTF 2018-25 {'yes' if ztf_ok else 'no'}"))
    return pd.DataFrame(rows)


def f4_rows() -> pd.DataFrame:
    e = pd.read_csv(ROOT / "hunts/H-0009/predictions/dr4_ensemble_sample.csv", dtype={"source_id": str, "alt_source_id": str})
    rows = []
    named = {k: v[0] for k, v in CASE_P_F4.items()}
    for r in e.itertuples():
        d7 = r.designation[:7]
        case = named.get(d7, r.case if isinstance(r.case, str) else "")
        insp = str(r.in_dr3_span) == "True"
        pl = float(r.p_lens_onstar) if pd.notna(r.p_lens_onstar) else (0.07 if insp else 0.17)
        why = []
        if d7 in CASE_P_F4:
            pl = CASE_P_F4[d7][1]
            why.append(f"{CASE_P_F4[d7][0]}: P(lens) {pl} from the case file (the ensemble's weight was {r.p_lens_onstar})")
        n30 = int(r.gost_n_fov_30)
        ps = 1.0 if n30 >= 3 else (0.7 if n30 == 2 else 0.3)
        m = 0.8
        if float(r.G) > 19:
            m *= 0.7
            why.append("G > 19 x0.7")
        if insp:
            m *= 0.6
            why.append("inside DR3's span, unflagged by DR3 x0.6")
        if d7 in named:
            m *= 1.5
            why.append("large, well-sampled optical event (ATLAS x6-9) x1.5")
        wr = (float(r.w_R) if pd.notna(r.w_R) else np.nan) + (float(r.w_F) if pd.notna(r.w_F) else 0.0)
        pr = wr if np.isfinite(wr) else 0.1 * (1 - pl)
        rows.append(dict(forecast="F4", key=r.designation, source_id=r.source_id, alt_source_id=r.alt_source_id or "",
                         ra=r.ra, dec=r.dec, t_event=float(r.t_event_mjd), case=case, G=float(r.G), p_lens=round(pl, 4),
                         p_sampled=ps, cat_mult=round(m, 4), p_nonlens_real=round(pr, 4), notes="; ".join(why)))
    t = pd.read_csv(ROOT / "hunts/H-0014/data/targets.csv", dtype={"source_id": str})
    ng = t[(t.set == "nogaia") & (t.t_event >= DR4_LO) & (t.t_event <= DR4_HI)]
    for r in ng.itertuples():
        rows.append(dict(forecast="F4", key=r.name, source_id="", alt_source_id="", ra=r.ra, dec=r.dec, t_event=r.t_event,
                         case="", G=np.nan, p_lens=0.15, p_sampled=0.15, cat_mult=0.56, p_nonlens_real=0.0,
                         notes="no Gaia DR3 source within 4\": only a new DR4 source could be catalogued"))
    return pd.DataFrame(rows)


def f5_rows() -> pd.DataFrame:
    t = pd.read_csv(ROOT / "hunts/H-0014/data/targets.csv", dtype={"source_id": str})
    t["source_id"] = t.source_id.fillna("")
    known_sets = t[t.set.isin(["strong", "strong_alt", "nogaia", "h0010", "cases", "sealed"])]
    excl_ids, excl_names = set(known_sets.source_id) - {""}, set(known_sets.name)
    st = pd.read_csv(ROOT / "hunts/H-0014/dryrun_dr3/epoch_status.csv", dtype={"release_source_id": str})
    dr3_lc = set(st[st.status == "ok"].release_source_id)
    u = t[(t.set == "unclassified") & (t.t_event >= DR4_LO) & (t.t_event <= DR4_HI)]
    n0 = len(u)
    u = u[~u.source_id.isin(excl_ids) & ~u.name.isin(excl_names)]
    n1 = len(u)
    u = u[~u.source_id.isin(dr3_lc)]
    print(f"F5 sample: {n0} unclassified events in DR4's span; {n0 - n1} dropped as strong events, H-0010 sources or case "
          f"stars; {n1 - len(u)} dropped because DR3 published their light curve (not blind); {len(u)} remain")
    k = [sum(DR4_LO <= x + o <= DR4_HI for o in G.RULES["f5_offsets"]) for x in u.t_event]
    return pd.DataFrame(dict(forecast="F5", key=u.name.to_numpy(), source_id=u.source_id.to_numpy(), alt_source_id="",
                             ra=u.ra.to_numpy(), dec=u.dec.to_numpy(), t_event=u.t_event.to_numpy(), n_controls=k,
                             notes=u.note.to_numpy()))


def main():
    print(f"numpy {np.__version__}, pandas {pd.__version__}, Python {sys.version.split()[0]}")
    f1 = f1_rows()
    f3 = f3_rows(f1)
    f4 = f4_rows()
    f5 = f5_rows()
    fc = {}

    r1 = G.model_f1(f1)
    f1["p_in"] = np.round(r1["p_in"], 4)
    a = r1["auc"]
    fin = np.isfinite(a)
    fc["F1"] = G.summary(r1["count"], G.GRADED["F1"])
    fc["F1"]["P_le_12"] = round(float(np.mean(r1["count"] <= 12)), 3)
    fc["F1"]["P_ge_37"] = round(float(np.mean(r1["count"] >= 37)), 3)
    fc["F1"]["P_c0_below_0.15"] = round(float(np.mean(r1["c0"] < 0.15)), 3)
    # F2 null: catalogue inclusion unrelated to Oddsky's score (the score permuted within each realisation)
    rng = np.random.default_rng(G.MC_SEED + 2)
    sc = f1.p_lens.to_numpy(float)[r1["f2"]]
    inc2 = r1["inc"][:, r1["f2"]]
    null = np.array([G.auc_fast(rng.permutation(sc), inc2[i]) for i in range(len(inc2))])
    mw = [G.auc_mw(sc, inc2[i])[1] for i in range(0, len(inc2), 10)]
    fc["F2"] = dict(threshold=G.GRADED["F2"], p_hit=round(float(np.mean(a[fin] > G.GRADED["F2"])), 3),
                    p_hit_if_unrelated=round(float(np.nanmean(null[np.isfinite(null)] > G.GRADED["F2"])), 3),
                    p_auc_gt_half=round(float(np.mean(a[fin] > 0.5)), 3),
                    p_mann_whitney_lt_005=round(float(np.nanmean(np.array(mw) < 0.05)), 3),
                    p_undefined=round(float(np.mean(~fin)), 4), auc_median=round(float(np.nanmedian(a)), 3),
                    auc_p10=round(float(np.nanpercentile(a, 10)), 3), auc_p90=round(float(np.nanpercentile(a, 90)), 3),
                    n=int(f1.f2_member.sum()))
    print("F1 by group (expected count):", f1.groupby("group").p_in.agg(["count", "sum"]).round(2).to_dict("index"))
    print("F1:", fc["F1"])
    print("F2:", fc["F2"])

    r3 = G.model_f3(f3)
    f3["p_fail"] = np.round(r3["p_fail"], 4)
    fc["F3"] = G.summary(r3["count"], G.GRADED["F3"])
    fc["F3"]["P_le"] = {k: round(float(np.mean(r3["count"] <= k)), 3) for k in range(0, 8)}
    print("F3:", fc["F3"])

    r4 = G.model_f4(f4)
    f4["p_in"] = np.round(r4["p_in"], 4)
    fc["F4"] = G.summary(r4["count"], G.GRADED["F4"])
    fc["F4"]["P_eq"] = {k: round(float(np.mean(r4["count"] == k)), 3) for k in range(0, 8)}
    fc["F4"]["corr_with_F1"] = round(float(np.corrcoef(r1["count"], r4["count"])[0, 1]), 3)
    fc["F4"]["expected_from_named_three"] = round(float(f4[f4.case.isin(["OS-0016", "OS-0020", "OS-0021"])].p_in.sum()), 3)
    print("F4:", fc["F4"])
    print("F4 named:", f4[f4.case != ""][["key", "case", "p_lens", "p_in"]].to_dict("records"))

    r5 = G.model_f5(f5.n_controls.to_numpy())
    ex = r5["excess"]
    fc["F5"] = dict(mean=round(float(np.nanmean(ex)), 4), median=round(float(np.nanmedian(ex)), 4),
                    p10=round(float(np.nanpercentile(ex, 10)), 4), p90=round(float(np.nanpercentile(ex, 90)), 4),
                    p_significant=round(float(np.mean(r5["significant"])), 3), n_events=len(f5),
                    n_pairs_expected=round(r5["n_pairs_expected"], 1))
    print("F5:", fc["F5"])

    cols = ["forecast", "key", "source_id", "alt_source_id", "case", "group", "ra", "dec", "G", "t_peak_dr3", "t_event",
            "p_lens", "cat_mult", "f_mult", "f2_member", "p_sampled", "p_nonlens_real", "r_lens", "r_nonlens_mult",
            "p_norepro", "n_controls", "p_in", "p_fail", "notes"]
    s = pd.concat([f1, f3, f4, f5], ignore_index=True).reindex(columns=cols)
    s.to_csv(PRED / "dr4_search_sample.csv", index=False)
    fc["versions"] = dict(numpy=np.__version__, pandas=pd.__version__, python=sys.version.split()[0])
    fc["mc"] = dict(n=G.MC_N, seed=G.MC_SEED)
    (HERE / "forecast.json").write_text(json.dumps(fc, indent=1))
    print("named sources:")
    print(f1[f1.case.ne("") | f1.key.str[:7].isin(["J174618", "J173332", "J072830"])][["key", "case", "group", "p_lens", "p_in"]]
          .to_string(index=False))
    print(f3[["key", "p_lens", "G", "p_norepro", "r_nonlens_mult", "p_fail"]].to_string(index=False))


if __name__ == "__main__":
    main()
