"""H-0015 s1: the target list, from Oddsky's committed lens lists (no network).

Every Oddsky lens or lens candidate whose event (or the astrometric tail of it) falls inside Gaia DR4's span
(2014-07-25 .. 2020-01-20), with what the photometry already says about it:

  * H-0010's 67 classifier-only Gaia DR3 MICROLENSING sources (hunts/H-0010/work/gaia_ml_unpub.csv; the referee's P(lens)
    from hunts/H-0010/README.md supersedes the first-pass column where they differ; catalogued lenses take the survey tE
    from `ref_intime`). Their events are Gaia DR3 peaks, all in 2014-2017. OS-0026, OS-0027 and OS-0029 are among them.
  * The 50 strong NEOWISE events of the sealed H-0009 ensemble sample (hunts/H-0009/predictions/dr4_ensemble_sample.csv),
    i.e. every strong H-0008/H-0009 event in DR4's span with a Gaia DR3 star, with its sealed P(lens on the star). OS-0016,
    OS-0020..OS-0025 are among them.
  * Lens cases with photometric fits (case files), which override the generic values: OS-0016, OS-0020, OS-0021,
    OS-0026, OS-0027, OS-0029; and the 2020-2022 lens cases OS-0017, OS-0018, OS-0019, whose events lie after DR4's span
    and whose deflection DR4 could see only as a pre-event tail.

Writes hunts/H-0015/data/targets_input.csv. Columns: name, source_id, set, case, p_lens, p_source, t0_mjd, t0_sig_d,
tE_lo, tE_hi, tE_source, piE_lo, piE_hi, amp_obs, nblock, G_list, ra_list, dec_list, note.
Run: uv run python -I hunts/H-0015/scripts/s1_targets.py
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "hunts/H-0015/data/targets_input.csv"


def MJD(s: str) -> float:
    return (pd.Timestamp(s) - pd.Timestamp("1858-11-17")).total_seconds() / 86400.0

# H-0010 referee (hunts/H-0010/README.md "After the referee" and "ATLAS follow-up"): P(lens) by name prefix.
H10_REFEREE = {
    "J174618": 0.75, "J173332": 0.75, "J072830": 0.60, "J144905": 0.45, "J200958": 0.45, "J174656": 0.42,
    "J151331": 0.42, "J175414": 0.42, "J171838": 0.42, "J182124": 0.60, "J172020": 0.20, "J180313": 0.10,
    "J184922": 0.10, "J182811": 0.25, "J180839": 0.50,  # OS-0029: its case file's P (H-0014 forecast table)
    "J171847": 0.30, "J174036": 0.30, "J174029": 0.30, "J171234": 0.30,
    "J182656": 0.30, "J190032": 0.30, "J184837": 0.30,
}

# Case files (cases/OS-00xx/case.yaml and the referee reports they cite). t0 in MJD; ranges are the cases' 95% ranges.
CASES = {
    "OS-0016": dict(source_id="170329679884731008", p_lens=0.95, t0_mjd=58012.2, t0_sig_d=3, tE_lo=47, tE_hi=56,
                    piE_lo=0.6, piE_hi=1.6, amp_obs=7.0,
                    tE_source="case: annual-parallax fit to NEOWISE+ATLAS (tE 47-56 d, |piE| 0.6-1.6)"),
    "OS-0020": dict(source_id="6020322385418675200", p_lens=0.75, t0_mjd=MJD("2017-08-15"), t0_sig_d=10, tE_lo=120,
                    tE_hi=190, piE_lo=0.25, piE_hi=0.55, amp_obs=7.0,
                    tE_source="case: ATLAS referee (tE 120-190 d, piE ~0.38 in every reduction)"),
    "OS-0021": dict(source_id="5952322268527918208", p_lens=0.55, t0_mjd=MJD("2018-07-12"), t0_sig_d=5, tE_lo=120,
                    tE_hi=490, piE_lo=np.nan, piE_hi=np.nan, amp_obs=7.7,
                    tE_source="case: ATLAS x7.7 peaking 2018 Jul 11-14, parallax needed, tE ~120-490 d"),
    "OS-0017": dict(source_id="6772245406602788608", p_lens=0.90, t0_mjd=MJD("2020-03-19"), t0_sig_d=3, tE_lo=40,
                    tE_hi=55, piE_lo=0.39, piE_hi=0.80, amp_obs=2.4,
                    tE_source="case: second referee, parallax fit (t0 2020 Mar 17-22, tE 40-55 d, piE 0.39-0.80); peak after DR4"),
    "OS-0018": dict(source_id="4158424169627436800", p_lens=0.95, t0_mjd=MJD("2022-09-19"), t0_sig_d=3, tE_lo=110,
                    tE_hi=133, piE_lo=np.nan, piE_hi=np.nan, amp_obs=5.4,
                    tE_source="case: ATLAS fit (tE 110-133 d); peak 2.7 yr after DR4"),
    "OS-0019": dict(source_id="4090003970570642816", p_lens=0.60, t0_mjd=MJD("2022-08-18"), t0_sig_d=7, tE_lo=40,
                    tE_hi=120, piE_lo=np.nan, piE_hi=np.nan, amp_obs=1.6,
                    tE_source="case: ATLAS/ZTF event ~4 months long (tE ~40-120 d assumed); peak 2.6 yr after DR4"),
}


def h0010() -> pd.DataFrame:
    h = pd.read_csv(ROOT / "hunts/H-0010/work/gaia_ml_unpub.csv", dtype={"source_id": str})
    rows = []
    for r in h.itertuples():
        key = r.name[:7]
        p = H10_REFEREE.get(key, r.p_lens)
        tE_lo = tE_hi = np.nan
        src = ""
        if isinstance(r.ref_intime, str) and "tE" in r.ref_intime:
            tes = [float(x) for x in re.findall(r"tE ([0-9.]+)", r.ref_intime)]
            tE_lo, tE_hi = 0.8 * min(tes), 1.25 * max(tes)
            src = f"survey tE {min(tes):.0f}-{max(tes):.0f} d (H-0010 ref_intime), +-25%"
        elif isinstance(r.tE_range, str) and (m := re.match(r"([0-9]+)-([0-9]+) d", r.tE_range)):
            # the H-0010 referee: 20 of 21 first-pass fits had a blend fraction at a bound, so these timescales are not
            # constrained; keep only the order of magnitude (the calibrated range widened by 2 each way)
            tE_lo, tE_hi = float(m.group(1)) / 2, float(m.group(2)) * 2
            src = "H-0010 Gaia-only static fit, 68% calibrated range widened x2 each way (blend fraction at a bound)"
        else:
            src = f"H-0010: {r.tE_range}"
        t0 = r.static_t0
        sig = 21.0
        if isinstance(r.t0_robust, str) and r.t0_robust.startswith(("before", "after")):
            sig = 60.0
        amp = pd.to_numeric(str(r.peak_amp).lstrip("<"), errors="coerce")
        set_ = ("case" if isinstance(r.case, str) else "h0010_known" if r.verdict == "known lens" else "h0010")
        rows.append(dict(name=r.name, source_id=r.source_id, set=set_, case=r.case if isinstance(r.case, str) else "",
                         p_lens=p, p_source="H-0010 referee" if key in H10_REFEREE else f"H-0010 ({r.verdict})",
                         t0_mjd=t0, t0_sig_d=sig, tE_lo=tE_lo, tE_hi=tE_hi, tE_source=src, piE_lo=np.nan, piE_hi=np.nan,
                         amp_obs=amp, nblock=np.nan, G_list=r.phot_g_mean_mag, ra_list=r.ra, dec_list=r.dec,
                         note=f"{r.verdict}; {r.known_as_x if isinstance(r.known_as_x, str) else ''}".strip("; ")))
    return pd.DataFrame(rows)


def strong() -> pd.DataFrame:
    e = pd.read_csv(ROOT / "hunts/H-0009/predictions/dr4_ensemble_sample.csv", dtype={"source_id": str})
    rows = []
    for r in e.itertuples():
        nb = int(r.nblock) if np.isfinite(r.nblock) else 1
        # NEOWISE samples every ~6 months: a one-visit event between quiet visits is shorter than a few months; an event
        # on two or more consecutive visits lasts at least that long. Loose ranges; the Galactic model does the rest.
        lo, hi = (5.0, 150.0) if nb == 1 else (60.0, 500.0)
        t0 = r.t_event_mjd if nb == 1 else (r.t_first + r.t_last) / 2
        rows.append(dict(name=r.designation, source_id=r.source_id, set="strong", case=r.case if isinstance(r.case, str) else "",
                         p_lens=r.p_lens_onstar, p_source="H-0009 sealed ensemble p_lens_onstar", t0_mjd=t0,
                         t0_sig_d=60.0 if nb == 1 else 90.0, tE_lo=lo, tE_hi=hi,
                         tE_source=f"NEOWISE {nb}-visit event: tE {lo:.0f}-{hi:.0f} d assumed", piE_lo=np.nan,
                         piE_hi=np.nan, amp_obs=r.neowise_ratio, nblock=nb, G_list=r.G, ra_list=r.ra, dec_list=r.dec,
                         note=f"NEOWISE x{r.neowise_ratio} on {r.event_date}; {r.status}"))
    return pd.DataFrame(rows)


def main():
    t = pd.concat([h0010(), strong()], ignore_index=True)
    for case, v in CASES.items():
        m = t.source_id == v["source_id"]
        upd = {**v, "case": case, "set": "case", "p_source": "case file"}
        if m.any():
            i = t.index[m][0]
            for k, val in upd.items():
                t.at[i, k] = val
            t = t[~m | (t.index == i)]
        else:
            t = pd.concat([t, pd.DataFrame([dict(name=case, nblock=np.nan, G_list=np.nan, ra_list=np.nan, dec_list=np.nan,
                                                 note="lens case; event after DR4's span", **upd)])], ignore_index=True)
    t.loc[t.case.isin(["OS-0017", "OS-0018", "OS-0019"]), "set"] = "case_after_span"
    t = t.drop_duplicates("source_id").reset_index(drop=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(OUT, index=False)
    print(t.groupby("set").size().to_string())
    print(f"{len(t)} targets -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
