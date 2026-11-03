"""Grader for hunts/H-0015/predictions/dr4_astrometric_forecast.md (F1-F5): Gaia DR4 epoch astrometry of Oddsky's lens
targets and of matched control stars. Reads only the outputs of the DR4-day `astrolens` stage
(src/oddsky/dr4day/astrometry.py), copied to hunts/H-0015/dr4/ with the run's id map, and the sealed sample file.

    uv run python -I hunts/H-0015/predictions/dr4_astrometric_grade.py                 # grade hunts/H-0015/dr4/
    uv run python -I hunts/H-0015/predictions/dr4_astrometric_grade.py --dir <path>    # another copy of the outputs
    uv run python -I hunts/H-0015/predictions/dr4_astrometric_grade.py --self-test     # on simulated outputs

Rules (fixed in the forecast document, section 2):
  inputs            <dir>/astrolens_results.csv, astrolens_status.csv and idmap.csv. Without idmap.csv the grader stops
                    (exit 2): the identity check is never skipped
  eligible          in the sample, status "fitted", not simulated, n_astro >= 20 transits, and its release id is the idmap's
                    match for its DR3 id (nearest within 0.5" and 0.3 mag; else the DR3 id itself)
  significant       dchi2 >= 25 and err_scale <= 3 and 0 < theta_e <= 50 mas
  F1  significant deflections among eligible F1 targets: TRUE if 2 <= count <= 6 (UNRESOLVABLE if < 75% eligible)
  F2  OS-0020: TRUE if M_ul95 finite and < 3 Msun; FALSE if eligible and not; UNRESOLVABLE if not eligible
  F3  OS-0021: TRUE if M_ul95 finite and < 5 Msun; FALSE if M_ul95 finite and >= 5, or significant with M_lo95 >= 5;
      UNRESOLVABLE if M_ul95 is unbounded (piE unconstrained) and not that, or if not eligible
  F4  OS-0016: TRUE if significant; FALSE if eligible and not; UNRESOLVABLE if not eligible
  F5  controls: TRUE if the significant fraction among eligible controls is < 1.5%; FALSE otherwise (UNRESOLVABLE if
      < 75% of the controls are eligible)
Prints one line per forecast and writes grade.json and grade_eligibility.csv next to the inputs. Exit 0 for any grade,
2 for unusable inputs.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SAMPLE = HERE / "dr4_astrometric_sample.csv"
F1_RANGE = (2, 6)
F2_MAX = 3.0
F3_MAX = 5.0
F5_MAX_FRAC = 0.015
MIN_ELIGIBLE_FRAC = 0.75
MIN_TRANSITS = 20
DCHI2 = 25.0
MAX_ERR_SCALE = 3.0
MAX_THETA = 50.0


class InputError(RuntimeError):
    pass


def significant(r) -> bool:
    return bool(r.dchi2 >= DCHI2 and r.err_scale <= MAX_ERR_SCALE and 0 < r.theta_e <= MAX_THETA)


def eligible_table(res: pd.DataFrame, status: pd.DataFrame, sample: pd.DataFrame, idmap: pd.DataFrame | None,
                   allow_simulated: bool = False) -> pd.DataFrame:
    st = status.drop_duplicates("source_id").set_index("source_id") if len(status) else pd.DataFrame()
    rs = res.drop_duplicates("source_id").set_index("source_id") if len(res) else pd.DataFrame()
    im = dict(zip(idmap.dr3_source_id, idmap.new_source_id, strict=False)) if idmap is not None else None
    rows = []
    for x in sample.itertuples():
        why = ""
        r = rs.loc[x.source_id] if x.source_id in rs.index else None
        if r is None:
            why = f"no fit ({st.loc[x.source_id].status if x.source_id in st.index else 'not in status'})"
        elif bool(r.get("simulated", False)) and not allow_simulated:
            why = "simulated (a dry run, not the release)"
        elif r.n_astro < MIN_TRANSITS:
            why = f"only {int(r.n_astro)} transits"
        elif im is not None and str(r.release_source_id) != str(im.get(x.source_id, x.source_id)):
            why = "release id is not the idmap match"
        g = (lambda c, r=r: float(r.get(c, np.nan))) if r is not None else (lambda c: np.nan)
        rows.append(dict(source_id=x.source_id, forecast=x.forecast, eligible=why == "", why=why,
                         significant=(significant(r) if r is not None and why == "" else False),
                         dchi2=g("dchi2"), theta_e=g("theta_e"), M_best=g("M_best"), M_lo95=g("M_lo95"), M_ul95=g("M_ul95"),
                         M_gt3_sigma=g("M_gt3_sigma")))
    return pd.DataFrame(rows)


def _count(e, tag, n_min_frac):
    s = e[e.forecast.str.contains(tag)]
    n, ne = len(s), int(s.eligible.sum())
    k = int((s.eligible & s.significant).sum())
    return s, n, ne, k, ne < n_min_frac * n


def grade(e: pd.DataFrame) -> dict:
    out = {}
    s, n, ne, k, short = _count(e, "F1", MIN_ELIGIBLE_FRAC)
    out["F1"] = (dict(outcome="UNRESOLVABLE", reason=f"{ne}/{n} eligible (< {MIN_ELIGIBLE_FRAC:.0%})", count=k) if short else
                 dict(outcome="TRUE" if F1_RANGE[0] <= k <= F1_RANGE[1] else "FALSE", count=k, eligible=ne, n=n,
                      significant=s[s.eligible & s.significant].source_id.tolist()))

    def one(tag, rule):
        r = e[e.forecast.str.contains(tag)]
        if len(r) != 1:
            return dict(outcome="UNRESOLVABLE", reason=f"{len(r)} sample rows for {tag}")
        r = r.iloc[0]
        if not r.eligible:
            return dict(outcome="UNRESOLVABLE", reason=r.why, source_id=r.source_id)
        outcome, why = rule(r)
        return dict(outcome=outcome, reason=why, source_id=r.source_id, dchi2=r.dchi2, theta_e=r.theta_e, M_best=r.M_best,
                    M_lo95=r.M_lo95, M_ul95=r.M_ul95, M_gt3_sigma=r.M_gt3_sigma)

    def f2(r):
        ok = bool(np.isfinite(r.M_ul95) and r.M_ul95 < F2_MAX)
        return ("TRUE" if ok else "FALSE"), f"M_ul95 = {r.M_ul95:.3g} Msun"

    def f3(r):
        heavy_detected = bool(r.significant and np.isfinite(r.M_lo95) and r.M_lo95 >= F3_MAX)
        if heavy_detected:
            return "FALSE", f"significant deflection with M_lo95 = {r.M_lo95:.3g} Msun"
        if not np.isfinite(r.M_ul95):
            return "UNRESOLVABLE", "M_ul95 unbounded: piE unconstrained"
        return ("TRUE" if r.M_ul95 < F3_MAX else "FALSE"), f"M_ul95 = {r.M_ul95:.3g} Msun"

    out["F2"] = one("F2", f2)
    out["F3"] = one("F3", f3)
    out["F4"] = one("F4", lambda r: ("TRUE" if r.significant else "FALSE", f"dchi2 = {r.dchi2:.1f}, theta_E = {r.theta_e:.3g} mas"))
    s, n, ne, k, short = _count(e, "F5", MIN_ELIGIBLE_FRAC)
    out["F5"] = (dict(outcome="UNRESOLVABLE", reason=f"{ne}/{n} controls eligible (< {MIN_ELIGIBLE_FRAC:.0%})", count=k)
                 if short else dict(outcome="TRUE" if k < F5_MAX_FRAC * ne else "FALSE", count=k, eligible=ne, n=n,
                                    fraction=round(k / max(ne, 1), 4), significant=s[s.eligible & s.significant].source_id.tolist()))
    return out


def run(d: Path, allow_simulated: bool = False, require_idmap: bool = True) -> dict:
    res_p, st_p, id_p = d / "astrolens_results.csv", d / "astrolens_status.csv", d / "idmap.csv"
    if not st_p.exists():
        raise InputError(f"no {st_p}: run scripts/dr4_day.py --release dr4 (stages idmap, epochs, astrolens) first")
    if require_idmap and not id_p.exists():
        raise InputError(f"no {id_p}: the astrolens stage copies the run's id map there; the identity check is required")
    sample = pd.read_csv(SAMPLE, dtype={"source_id": str})
    res = pd.read_csv(res_p, dtype={"source_id": str, "release_source_id": str}) if res_p.exists() and res_p.stat().st_size > 1 else pd.DataFrame()
    st = pd.read_csv(st_p, dtype={"source_id": str, "release_source_id": str})
    idmap = pd.read_csv(id_p, dtype={"dr3_source_id": str, "new_source_id": str}) if id_p.exists() else None
    e = eligible_table(res, st, sample, idmap, allow_simulated)
    g = grade(e)
    g["meta"] = dict(inputs=str(d), numpy=np.__version__, pandas=pd.__version__, python=sys.version.split()[0],
                     n_sample=len(sample), n_eligible=int(e.eligible.sum()), idmap=id_p.exists())
    e.to_csv(d / "grade_eligibility.csv", index=False)
    (d / "grade.json").write_text(json.dumps(g, indent=1, default=str))
    for k in ("F1", "F2", "F3", "F4", "F5"):
        print(k, g[k]["outcome"], {kk: v for kk, v in g[k].items() if kk not in ("outcome", "significant")})
    return g


# ---------------------------------------------------------------- self-test
def _synthetic(sample, n_sig, f2_ul, f3, f4_sig, n_ctrl_sig=0, missing=0, rng=None):
    """Synthetic stage outputs with known answers. f3 = (M_ul95, significant, M_lo95)."""
    rng = np.random.default_rng(0) if rng is None else rng
    rows, st = [], []
    f1 = sample[sample.forecast.str.contains("F1")].source_id.tolist()
    special = set(sample[sample.forecast.str.contains("F2|F3|F4")].source_id)
    pool = [s for s in f1 if s not in special]
    sig = set(rng.choice(pool, size=n_sig, replace=False)) if n_sig else set()
    ctrl = sample[sample.forecast.str.contains("F5")].source_id.tolist()
    csig = set(rng.choice(ctrl, size=n_ctrl_sig, replace=False)) if n_ctrl_sig else set()
    drop = set(rng.choice(sorted(set(pool) - sig), size=missing, replace=False)) if missing else set()
    for x in sample.itertuples():
        if x.source_id in drop:
            st.append(dict(source_id=x.source_id, release_source_id=x.source_id, status="no epoch astrometry"))
            continue
        r = dict(source_id=x.source_id, release_source_id=x.source_id, simulated=False, n_astro=60, err_scale=1.0,
                 dchi2=float(rng.uniform(0, 8)), theta_e=float(rng.uniform(0, 1)), M_best=0.3, M_lo95=0.01, M_ul95=2.0,
                 M_gt3_sigma=0.0)
        if x.source_id in sig or x.source_id in csig:
            r.update(dchi2=60.0, theta_e=2.0, M_best=0.8, M_lo95=0.3, M_ul95=1.5)
        if "F2" in x.forecast:
            r.update(M_ul95=f2_ul)
        if "F3" in x.forecast:
            r.update(M_ul95=f3[0], dchi2=80.0 if f3[1] else 3.0, theta_e=6.0 if f3[1] else 0.4, M_lo95=f3[2])
        if "F4" in x.forecast:
            r.update(dchi2=80.0 if f4_sig else 3.0, theta_e=1.2)
        rows.append(r)
        st.append(dict(source_id=x.source_id, release_source_id=x.source_id, status="fitted"))
    idm = pd.DataFrame(dict(dr3_source_id=sample.source_id, new_source_id=sample.source_id))
    return pd.DataFrame(rows), pd.DataFrame(st), idm


def _write(d, res, st, idm):
    res.to_csv(d / "astrolens_results.csv", index=False)
    st.to_csv(d / "astrolens_status.csv", index=False)
    if idm is not None:
        idm.to_csv(d / "idmap.csv", index=False)
    elif (d / "idmap.csv").exists():
        (d / "idmap.csv").unlink()


def self_test() -> bool:
    sample = pd.read_csv(SAMPLE, dtype={"source_id": str})
    inf = float("inf")
    cases = [  # args -> expected outcomes
        ((2, 1.5, (3.0, False, 0.1), True, 0), dict(F1="TRUE", F2="TRUE", F3="TRUE", F4="TRUE", F5="TRUE")),
        ((0, 4.0, (8.0, False, 0.1), False, 30), dict(F1="FALSE", F2="FALSE", F3="FALSE", F4="FALSE", F5="FALSE")),
        ((9, inf, (inf, False, 0.1), True, 0), dict(F1="FALSE", F2="FALSE", F3="UNRESOLVABLE", F4="TRUE")),
        ((3, 1.0, (inf, True, 7.0), True, 0), dict(F3="FALSE")),
        ((3, 1.0, (3.0, False, 0.1), True, 0, 40), dict(F1="UNRESOLVABLE", F2="TRUE")),
    ]
    ok = True
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        for args, want in cases:
            _write(d, *_synthetic(sample, *args))
            g = run(d)
            for k, v in want.items():
                if g[k]["outcome"] != v:
                    print(f"SELF-TEST FAIL: {args} -> {k} {g[k]['outcome']} (want {v})")
                    ok = False
        res, st, idm = _synthetic(sample, 2, 1.5, (3.0, False, 0.1), True)
        # identity: a release id that is not the idmap match makes the target ineligible
        bad = idm.copy()
        f4 = sample[sample.forecast.str.contains("F4")].source_id.iloc[0]
        bad.loc[bad.dr3_source_id == f4, "new_source_id"] = "999"
        _write(d, res, st, bad)
        if run(d)["F4"]["outcome"] != "UNRESOLVABLE":
            print("SELF-TEST FAIL: identity mismatch was graded")
            ok = False
        # no idmap: refuse to grade
        _write(d, res, st, None)
        try:
            run(d)
            print("SELF-TEST FAIL: graded without idmap.csv")
            ok = False
        except InputError:
            pass
        # simulated rows (the DR3 dry run) are never graded
        res2 = res.copy()
        res2["simulated"] = True
        _write(d, res2, st, idm)
        g = run(d)
        if not all(g[k]["outcome"] == "UNRESOLVABLE" for k in ("F1", "F2", "F3", "F4", "F5")):
            print("SELF-TEST FAIL: simulated outputs were graded")
            ok = False
    dry = HERE.parent / "dryrun_dr3"
    if (dry / "astrolens_status.csv").exists():
        with tempfile.TemporaryDirectory() as td:
            for f in ("astrolens_results.csv", "astrolens_status.csv"):
                if (dry / f).exists():
                    (Path(td) / f).write_bytes((dry / f).read_bytes())
            g = run(Path(td), require_idmap=False)
            if not all(g[k]["outcome"] == "UNRESOLVABLE" for k in ("F1", "F2", "F3", "F4", "F5")):
                print("SELF-TEST FAIL: the DR3 dry run was graded")
                ok = False
    print("SELF-TEST", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(HERE.parent / "dr4"))
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return 0 if self_test() else 1
    try:
        run(Path(a.dir))
    except InputError as e:
        print(f"ERROR: {e}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
