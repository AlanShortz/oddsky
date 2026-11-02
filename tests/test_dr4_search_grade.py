"""The grader of the H-0014 DR4-day search forecasts (hunts/H-0014/predictions/dr4_search_grade.py). Offline."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
PRED = ROOT / "hunts/H-0014/predictions"
spec = importlib.util.spec_from_file_location("dr4_search_grade", PRED / "dr4_search_grade.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)

DR4 = G.RELEASES["dr4"]


def lc(t_peak=None, amp_mag=0.0, width=20.0, t=None, base=17.0, seed=0, extra=None):
    """Synthetic per-transit G/BP/RP photometry in gaia_epoch.to_series format: pairs of transits 106 min apart."""
    rng = np.random.default_rng(seed)
    t = np.sort(np.r_[np.arange(56870, 58860, 37.0), np.arange(56870, 58860, 37.0) + 0.0736]) if t is None else np.asarray(t)
    m = base + rng.normal(0, 0.01, t.size)
    for tp, a in ([(t_peak, amp_mag)] if t_peak is not None else []) + (extra or []):
        m -= a * np.exp(-0.5 * ((t - tp) / width) ** 2)
    rows = []
    for i, (tt, mm) in enumerate(zip(t, m, strict=True)):
        for b, off in (("G", 0.0), ("BP", 0.6), ("RP", -0.7)):
            rows.append(dict(t_mjd=tt, mag=mm + off, err=0.01, band=b, survey="GAIA", flag="", camera=str(1000 + i)))
    return pd.DataFrame(rows)


def write_run(tmp: Path, cat: pd.DataFrame | None = None, idmap: pd.DataFrame | None = None, flags=None, metrics=None,
              epochs: dict | None = None, status: dict | None = None) -> Path:
    run = tmp / "run"
    (run / "catalogue").mkdir(parents=True)
    (run / "search").mkdir()
    (run / "epoch").mkdir()
    if cat is not None:
        cat.to_csv(run / "catalogue/lens_catalogue.csv", index=False)
    if idmap is not None:
        idmap.to_csv(run / "idmap.csv", index=False)
    if flags is not None:
        pd.DataFrame(dict(source_id=flags)).to_csv(run / "catalogue/target_flags.csv", index=False)
    if metrics is not None:
        metrics.to_csv(run / "search/metrics.csv", index=False)
    for k, v in (epochs or {}).items():
        v.to_csv(run / "epoch" / f"{k}.csv", index=False)
    if status is not None:
        pd.DataFrame(dict(release_source_id=list(status), status=list(status.values()))).to_csv(run / "epoch_status.csv",
                                                                                                  index=False)
    return run


def cat_frame(tmp: Path, **cols) -> pd.DataFrame:
    p = tmp / "cat.csv"
    pd.DataFrame(cols).to_csv(p, index=False)
    return G.catalogue_frame(p)


# ---- helpers ----------------------------------------------------------------------------------------------------------
def test_sid_and_time_units():
    assert G.sid("4067152339419332992") == "4067152339419332992"
    assert G.sid("4067152339419332992.0") == "4067152339419332992"
    assert G.sid(float("nan")) == "" and G.sid("") == "" and G.sid("abc") == ""
    x = G.to_mjd(pd.Series([2150.5221928, 57347.52, 2457348.02, np.nan]))
    assert x.iloc[0] == pytest.approx(57347.5222, abs=1e-3)   # Gaia DR3 tmax (BJD_TCB - 2455197.5)
    assert x.iloc[1] == pytest.approx(57347.52)               # already MJD
    assert x.iloc[2] == pytest.approx(57347.52)               # JD
    assert np.isnan(x.iloc[3])


def test_catalogue_frame_uses_lookup_lists_only(tmp_path, monkeypatch):
    c = cat_frame(tmp_path, source_id=["1234567", "7654321"], paczynski0_tmax=[2150.5, 2500.0], paczynski0_te=[40.0, 80.0],
                  ra=[10.0, 11.0], dec=[-5.0, -6.0])
    assert list(c.tmax_mjd.round(1)) == [57347.5, 57697.0] and list(c.tE) == [40.0, 80.0]
    # an unlisted rename is NOT picked up ...
    c = cat_frame(tmp_path, source_id=["1234567"], model_tmax_bjd=[2458000.5])
    assert c.attrs["time_column"] is None and c.tmax_mjd.isna().all() and c.ra.isna().all()
    # ... until the name is appended to the list (section 6 item 1)
    monkeypatch.setitem(G.COLUMNS, "tmax", G.COLUMNS["tmax"] + ["model_tmax_bjd"])
    c = cat_frame(tmp_path, source_id=["1234567"], model_tmax_bjd=[2458000.5])
    assert c.tmax_mjd.iloc[0] == pytest.approx(58000.0)
    with pytest.raises(KeyError):
        cat_frame(tmp_path, sid=["1"])


def test_bug4_peak_time_always_from_raw_column(tmp_path):
    """The pipeline writes tmax_mjd = paczynski0_tmax + 55197 even if DR4 gives MJD or JD. The grader must ignore it."""
    for raw in (58000.0, 2458000.5, 2803.0):
        c = cat_frame(tmp_path, source_id=["1"], paczynski0_tmax=[raw], tmax_mjd=[raw + 55197.0])
        assert c.tmax_mjd.iloc[0] == pytest.approx(58000.0, abs=0.01), raw


def test_auc_mw():
    auc, p = G.auc_mw([0.9, 0.8, 0.7, 0.2, 0.1, 0.1], [1, 1, 1, 0, 0, 0])
    assert auc == 1.0 and p < 0.05
    auc, _ = G.auc_mw([0.5, 0.5, 0.5, 0.5], [1, 0, 1, 0])
    assert auc == 0.5
    assert np.isnan(G.auc_mw([0.1, 0.2], [0, 0])[0])
    assert G.auc_fast(np.array([0.9, 0.1, 0.5]), np.array([True, False, False])) == 1.0


def test_parse_eps():
    assert G.parse_eps("57106:-1.61:4;58500:-0.40:3") == [(57106.0, -1.61, 4), (58500.0, -0.40, 3)]
    assert G.parse_eps(np.nan) == [] and G.parse_eps("bad;1:2") == []


# ---- F1 / F2 ----------------------------------------------------------------------------------------------------------
def f1_sample():
    return pd.DataFrame(dict(forecast="F1", key=["A", "B", "C", "D"], source_id=["111111", "222222", "333333", "444444"],
                             ra=[10.0, 20.0, 30.0, 40.0], dec=[0.0, 0.0, 0.0, 0.0],
                             group=["known lens", "first-pass candidate", "inconclusive", "not a lens"],
                             p_lens=[0.97, 0.7, 0.3, 0.05], cat_mult=[1.15, 1.0, 1.0, 1.0], f_mult=[2.0, 2.0, 2.0, 1.0],
                             f2_member=[False, True, True, True], p_in=[0.6, 0.4, 0.3, 0.1], t_peak_dr3=57000.0))


def test_f1_matches_by_idmap_and_position(tmp_path, monkeypatch):
    monkeypatch.setitem(G.RULES, "f1_min_identity", 3)
    cat = cat_frame(tmp_path, source_id=["999111", "555555"], ra=[np.nan, 20.0 + 0.3 / 3600], dec=[np.nan, 0.0],
                    paczynski0_tmax=[1803.0, 1813.0])
    g, r = G.grade_f1_f2(f1_sample(), cat, {"111111": "999111"}, kn={"999111", "222222", "333333"})
    assert list(g.in_catalogue) == [True, True, False, False]
    assert g.by_pos.tolist() == [False, True, False, False]      # B only by position (0.3" < 0.5")
    assert g.identity.tolist() == [True, True, True, False]
    assert r["F1"]["statistic"] == 2 and r["F1"]["bounds"] == [13, 36] and not r["F1"]["hit"]
    # F2 over the identified F2 members (B in, C out): AUC 1.0 > 0.60
    assert r["F2"]["statistic"] == 1.0 and r["F2"]["hit"] and r["F2"]["n"] == 2 and r["F2"]["threshold"] == 0.60


def test_f2_threshold_is_060(tmp_path, monkeypatch):
    monkeypatch.setitem(G.RULES, "f1_min_identity", 1)
    s = f1_sample().assign(p_lens=[0.97, 0.5, 0.5, 0.5], f2_member=True)
    cat = cat_frame(tmp_path, source_id=["111111", "222222"], paczynski0_tmax=[1803.0, 1813.0])
    g, r = G.grade_f1_f2(s, cat, {}, kn=set(s.source_id))
    # scores: in {0.97, 0.5}, out {0.5, 0.5}: AUC = (1 + 1 + 0.5 + 0.5) / 4 = 0.75 -> hit; ties at 0.5 only would be 0.5
    assert r["F2"]["statistic"] == 0.75 and r["F2"]["hit"]
    g, r = G.grade_f1_f2(s.assign(p_lens=0.5), cat, {}, kn=set(s.source_id))
    assert r["F2"]["statistic"] == 0.5 and not r["F2"]["hit"] and not r["F2"]["reported_auc_gt_half"]


def test_f2_not_graded_when_nothing_is_catalogued(tmp_path, monkeypatch):
    monkeypatch.setitem(G.RULES, "f1_min_identity", 1)
    cat = cat_frame(tmp_path, source_id=["8"], paczynski0_tmax=[1803.0])
    g, r = G.grade_f1_f2(f1_sample(), cat, {}, set(f1_sample().source_id))
    assert r["F1"]["statistic"] == 0 and not r["F1"]["hit"]
    assert r["F2"]["statistic"] is None and "not graded" in r["F2"]["verdict"]


def test_bug2_identity_floor(tmp_path):
    """An empty or partial target_flags.csv must not shrink the sample: below 60 identities F1 and F2 are not resolvable."""
    s = pd.concat([f1_sample()] * 17, ignore_index=True)   # 68 rows
    s["source_id"] = [str(100000 + i) for i in range(len(s))]
    cat = cat_frame(tmp_path, source_id=s.source_id[:5].tolist(), paczynski0_tmax=[1803.0] * 5)
    g, r = G.grade_f1_f2(s, cat, {}, kn=set())               # empty flags: only the 5 catalogued have an identity
    assert r["F1"]["statistic"] is None and r["F1"]["verdict"].startswith("not yet resolvable")
    assert r["F2"]["statistic"] is None and r["F1"]["n_with_identity"] == 5
    g, r = G.grade_f1_f2(s, cat, {}, kn=set(s.source_id[:60]))
    assert r["F1"]["statistic"] == 5 and r["F1"]["n_with_identity"] == 60
    run = write_run(tmp_path / "r", cat=pd.DataFrame(dict(source_id=["1"], paczynski0_tmax=[1803.0])))
    assert G.known_ids(run) == set()                          # no flags file -> nobody has an identity


# ---- F3 ---------------------------------------------------------------------------------------------------------------
def f3_case(tmp_path, monkeypatch, eps: str, df: pd.DataFrame | None, label="lens-like brightening", status="ok"):
    monkeypatch.setitem(G.RULES, "f3_min_testable", 1)
    s = pd.DataFrame(dict(forecast="F3", key=["X"], source_id=["123456789"], p_fail=[0.2], t_peak_dr3=[57106.0],
                          p_lens=[0.5], r_lens=[0.02], r_nonlens_mult=[1.0], p_norepro=[0.02]))
    m = pd.DataFrame(dict(source_id=["123456789"], release_source_id=["123456789"], set=["h0010"], label=[label],
                          bright_eps=[eps]))
    run = write_run(tmp_path, metrics=m, epochs={"123456789": df} if df is not None else {},
                    status={"123456789": status})
    return G.grade_f3(s, run, DR4, pd.read_csv(run / "search/metrics.csv", dtype=str), G.epoch_status(run))


def test_f3_single_reproduced_event_passes(tmp_path, monkeypatch):
    g, r = f3_case(tmp_path, monkeypatch, "57106:-1.20:4", lc(57106, 1.2))
    assert g.testable.iloc[0] and g.reproduced.iloc[0] and not g.repeat.iloc[0]
    assert r["F3"]["statistic"] == 0 and r["F3"]["bounds"] == [2, 6] and not r["F3"]["hit"]


def test_f3_new_repeat_fails(tmp_path, monkeypatch):
    g, r = f3_case(tmp_path, monkeypatch, "57106:-1.20:4;58400:-0.45:3", lc(57106, 1.2, extra=[(58400, 0.45)]))
    assert g.repeat.iloc[0] and r["F3"]["statistic"] == 1
    for eps in ("57106:-1.2:4;58400:-0.25:5", "57106:-1.2:4;58400:-0.6:2", "57106:-1.2:4;57700:-0.6:5"):
        g, r = f3_case(tmp_path / eps.replace(":", "_").replace(";", "_"), monkeypatch, eps, lc(57106, 1.2))
        assert not g.repeat.iloc[0], eps


def test_f3_not_reproduced_and_untestable(tmp_path, monkeypatch):
    g, r = f3_case(tmp_path, monkeypatch, "", lc(), label="quiet")    # a valid DR4 verdict with nothing at the DR3 peak
    assert g.testable.iloc[0] and not g.reproduced.iloc[0] and r["F3"]["statistic"] == 1
    early = lc(57106, 1.2, t=np.arange(56870, 57900, 10.0))            # no transits after DR3's span
    g, r = f3_case(tmp_path / "b", monkeypatch, "57106:-1.20:4", early)
    assert not g.testable.iloc[0] and "untestable" in g.note.iloc[0]
    assert r["F3"]["statistic"] is None and r["F3"]["verdict"].startswith("void")
    g, r = f3_case(tmp_path / "c", monkeypatch, "", None, status="absent")   # the archive has no epoch photometry
    assert not g.testable.iloc[0] and r["F3"]["verdict"].startswith("void")


@pytest.mark.parametrize("label", ["analysis error: ValueError: x", "", None, float("nan"), "too few G transits"])
def test_bug1_analysis_error_or_empty_label_is_untestable_not_a_fail(tmp_path, monkeypatch, label):
    g, r = f3_case(tmp_path, monkeypatch, "", lc(57106, 1.2), label=label)
    assert not g.testable.iloc[0] and g.fail.iloc[0] is None
    assert r["F3"]["statistic"] is None                      # void (0 testable), never counted as a failure


@pytest.mark.parametrize("bad", ["error", "missing (archive says it has epoch photometry)"])
def test_bug3_incomplete_epoch_run_is_not_resolvable(tmp_path, monkeypatch, bad):
    g, r = f3_case(tmp_path, monkeypatch, "57106:-1.20:4", lc(57106, 1.2), status=bad)
    assert r["F3"]["statistic"] is None and r["F3"]["verdict"] == "not yet resolvable: incomplete run"
    run = write_run(tmp_path / "f5", epochs={"5001": lc(58000, 1.0)}, status={"5001": "ok", "5002": bad})
    ev = pd.DataFrame(dict(key=["a", "b"], source_id=["5001", "5002"], t_event=[58000.0, 58000.0]))
    _, r5 = G.grade_f5(ev, run, DR4, {}, G.epoch_status(run))
    assert r5["F5"]["statistic"] is None and r5["F5"]["verdict"] == "not yet resolvable: incomplete run"
    # a source the epochs stage never reached, or no status file at all, is also incomplete
    assert G.epoch_completeness({"5001": "ok"}, ["5001", "5002"]) == ["5002: not in epoch_status.csv"]
    assert G.epoch_completeness(None, ["5001"]) == ["no epoch_status.csv"]
    # status ok but no cached light curve: incomplete, not untestable
    g, r = f3_case(tmp_path / "nocache", monkeypatch, "57106:-1.20:4", None, status="ok")
    assert r["F3"]["verdict"] == "not yet resolvable: incomplete run"


# ---- F4 ---------------------------------------------------------------------------------------------------------------
def f4_sample():
    return pd.DataFrame(dict(forecast="F4", key=["E1", "E2", "E3", "E4"], source_id=["1001", "1002", "1003", ""],
                             alt_source_id=["", "2002", "", ""], ra=[100.0, 110.0, 120.0, 130.0], dec=[-20.0] * 4,
                             t_event=[58000.0, 58300.0, 58500.0, 58700.0], p_in=0.2, case=["OS-0016", "", "", ""]))


def test_f4_position_id_and_time_window(tmp_path):
    cat = cat_frame(tmp_path, source_id=["777", "2002", "1003", "888"],
                    ra=[100.0 + 2.0 / 3600, np.nan, 120.0, 130.0 + 10 / 3600], dec=[-20.0, np.nan, -20.0, -20.0],
                    paczynski0_tmax=[58050.0 - 55197, 58200.0 - 55197, 58800.0 - 55197, 58700.0 - 55197],
                    paczynski0_te=[np.nan, 60.0, 50.0, 30.0])
    g, r = G.grade_f4(f4_sample(), cat, {})
    # E1: 2" away, 50 d (<= 60 d): yes. E2: neighbour id, 100 d <= 2 tE = 120 d: yes. E3: right star, 300 d late: no.
    # E4: no Gaia star; nearest lens 10" away: no.
    assert g.catalogued.tolist() == [True, True, False, False]
    assert r["F4"]["statistic"] == 2 and r["F4"]["hit"] and r["F4"]["named"] == {"OS-0016": True}


def test_f4_time_window_capped_at_365_d(tmp_path):
    cat = cat_frame(tmp_path, source_id=["1001", "1003"], paczynski0_tmax=[58000.0 + 400 - 55197, 58500.0 + 300 - 55197],
                    paczynski0_te=[5000.0, 5000.0])
    g, _ = G.grade_f4(f4_sample(), cat, {})
    assert g.catalogued.tolist() == [False, False, True, False]   # 400 d > 365 d cap; 300 d inside


def test_bug4_f4_not_resolvable_on_bad_time_zero_point_or_no_time(tmp_path):
    bad = cat_frame(tmp_path, source_id=["1001", "1003"], paczynski0_tmax=[30000.0, 31000.0])   # neither Gaia time nor MJD
    g, r = G.grade_f4(f4_sample(), bad, {})
    assert r["F4"]["statistic"] is None and "time zero point" in r["F4"]["verdict"]
    none = cat_frame(tmp_path, source_id=["1001"], ra=[100.0], dec=[-20.0])
    g, r = G.grade_f4(f4_sample(), none, {})
    assert r["F4"]["statistic"] is None and "no peak-time column" in r["F4"]["verdict"]


# ---- F5 ---------------------------------------------------------------------------------------------------------------
def test_f5_pass_at_event_and_not_at_controls(tmp_path):
    eps = {"5001": lc(58000, 1.0, seed=1), "5002": lc(seed=2), "5003": lc(57300, 0.8, seed=3)}
    run = write_run(tmp_path, epochs=eps)
    ev = pd.DataFrame(dict(key=["a", "b", "c", "d"], source_id=["5001", "5002", "5003", "5004"],
                           t_event=[58000.0, 58000.0, 57300.0, 58000.0]))
    e = G.f5_events(ev, run, DR4, {})
    assert e.true_status.tolist() == ["pass", "fail", "pass", "no light curve"]
    assert e.n_ctrl_pass.sum() == 0 and (e.n_ctrl_testable[:3] > 0).all()
    st = G.f5_statistic(e)
    assert st["n_pairs"] == 3 and st["excess"] == pytest.approx(2 / 3, abs=1e-4) and st["pass_rate_control"] == 0


def test_f5_signs_flipped_per_star():
    """Events on one Gaia star share a sign: two passing events on one star are one unit, not two."""
    ev = pd.DataFrame(dict(true_status=["pass", "pass", "fail"], n_ctrl_testable=[2, 2, 2], n_ctrl_pass=[0, 0, 0],
                           source_id=["S1", "S1", "S2"]))
    st = G.f5_statistic(ev)
    assert st["n_stars"] == 2 and st["n_pairs"] == 3
    # stars: S1 carries d = (1, 1), S2 d = 0; the flipped mean is >= observed only when S1's sign is +: p ~ 0.5
    assert 0.45 < st["p_one_sided"] < 0.55
    ev2 = ev.assign(source_id=["S1", "S3", "S2"])           # independent stars: p ~ 0.25
    assert 0.2 < G.f5_statistic(ev2)["p_one_sided"] < 0.3


def test_f5_complete_run_is_graded(tmp_path, monkeypatch):
    monkeypatch.setitem(G.RULES, "f5_min_pairs", 2)
    run = write_run(tmp_path, epochs={"5001": lc(58000, 1.0, seed=1), "5002": lc(seed=2)},
                    status={"5001": "ok", "5002": "ok", "5003": "absent"})
    ev = pd.DataFrame(dict(key=["a", "b", "c"], source_id=["5001", "5002", "5003"], t_event=[58000.0] * 3))
    _, r = G.grade_f5(ev, run, DR4, {}, G.epoch_status(run))
    assert r["F5"]["n_pairs"] == 2 and r["F5"]["excess"] == 0.5 and "hit" in r["F5"]


# ---- the sample, the forecast numbers and the driver -------------------------------------------------------------------
def test_sealed_sample_and_forecast_are_consistent():
    s = G.load_sample()
    assert s.groupby("forecast").size().to_dict() == {"F1": 67, "F3": 21, "F4": 61, "F5": 444}
    f1 = s[s.forecast == "F1"]
    assert f1.f2_member.astype(bool).sum() == 39 and f1.source_id.str.len().ge(15).all()
    assert s[s.forecast == "F4"].source_id.eq("").sum() == 11          # the no-Gaia-star events
    # case P(lens) from the case files
    p = dict(zip(s.case.fillna(""), s.p_lens, strict=False))
    assert (p["OS-0016"], p["OS-0020"], p["OS-0021"], p["OS-0026"], p["OS-0027"], p["OS-0029"]) == (0.95, 0.75, 0.55, 0.65,
                                                                                                      0.60, 0.50)
    fc = json.loads(G.FORECAST.read_text())
    assert fc["F1"]["bounds"] == [13, 36] and fc["F3"]["bounds"] == [2, 6] and fc["F4"]["bounds"] == [2, 6]
    assert fc["F2"]["threshold"] == 0.60
    r = G.model_f3(s[s.forecast == "F3"])
    assert G.summary(r["count"], (2, 6))["p_hit"] == fc["F3"]["p_hit"]


def test_grade_never_writes_into_predictions(tmp_path):
    run = write_run(tmp_path)
    with pytest.raises(SystemExit):
        G.grade(run, "dr4", out=PRED / "work", only=("F4",), quiet=True)


def _hashes():
    return {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(PRED.rglob("*")) if p.is_file()
            and "__pycache__" not in p.parts}


def test_self_test_on_dr3_dry_run_leaves_sealed_files_untouched():
    run = G.default_run(G.RELEASES["dr3"])
    if not (run / "epoch").exists() or not (run / "catalogue/lens_catalogue.csv").exists():
        pytest.skip("needs the DR3 dry run's outputs (~/oddsky-runs/h0014/dr3)")
    before = _hashes()
    assert G.self_test(run)
    assert _hashes() == before
