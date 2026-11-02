"""H-0012 merge/triage (hunts/H-0012/scripts/merge_triage.py): merge rule, units, triage classes,
scores, TNS parsing and the 'HTTP 429 is an error, never nothing' rule. No network."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

P = Path(__file__).resolve().parents[1] / "hunts" / "H-0012" / "scripts" / "merge_triage.py"
spec = importlib.util.spec_from_file_location("merge_triage", P)
mt = importlib.util.module_from_spec(spec)
sys.modules["merge_triage"] = mt
spec.loader.exec_module(mt)


@pytest.fixture(autouse=True)
def _cache(tmp_path, monkeypatch):
    monkeypatch.setattr(mt, "CACHE", tmp_path)
    monkeypatch.setattr(mt, "TNS_PACE_S", 0.0)


def targets():
    return pd.DataFrame(dict(Name=["GALA", "GALB"], ra=[10.0, 10.02], dec=[20.0, 20.0], a26=[4.0, 1.0],
                             r_arcmin=[2.0, 0.5], ell_a=[2.0, 0.5], ell_ba=[1.0, 1.0], ell_pa=[0.0, 0.0], dist_mpc=[5.0, 5.0], dist_source=["x", "x"],
                             search_diam_arcmin=[4.8, 1.2]), index=["GALA", "GALB"])


def test_luminosity_matches_readme_limit():
    # README: W1 5-sigma limit 17.36 mag at 0.77 Mpc is 5.8e2 L_sun
    f_nmgy = 10 ** ((22.5 - 17.36) / 2.5)
    L = mt.nu_lnu_lsun(mt.nmgy_to_ujy(f_nmgy, 1), 1, 0.77)
    assert L == pytest.approx(5.8e2, rel=0.02)
    # inverse-square scaling
    assert mt.nu_lnu_lsun(10.0, 2, 10.0) / mt.nu_lnu_lsun(10.0, 2, 1.0) == pytest.approx(100)


def test_vega_colour():
    assert mt.vega_colour(100.0, 100.0) == pytest.approx(0.0)
    assert mt.vega_colour(100.0, 251.18864) == pytest.approx(1.0, abs=1e-4)
    assert np.isnan(mt.vega_colour(-1.0, 10.0))


def test_merge_keeps_tile_furthest_from_edge_and_nearest_galaxy():
    d = 1.5 / 3600  # 1.5" apart: the same source
    df = pd.DataFrame(dict(
        uid=["GALA|t1|1", "GALA|t2|7", "GALB|t2|3", "GALA|t1|2"],
        galaxy=["GALA", "GALA", "GALB", "GALA"], tile=["t1", "t2", "t2", "t1"], group=[1, 7, 3, 2],
        ra=[10.019, 10.019 + d, 10.019, 9.99], dec=[20.0, 20.0, 20.0 + d, 20.0],
        edge_px=[12.0, 400.0, 400.0, 300.0], has_lc=[True, True, True, True]))
    out = mt.merge_candidates(df, targets())
    assert len(out) == 2
    m = out[out.n_tiles > 1].iloc[0]
    assert m.tile == "t2"  # furthest from the edge
    assert m.galaxy == "GALB"  # 0.02 deg from GALB's centre = 0.04 radii... nearer in r/a than GALA
    assert set(m.merged_uids.split(";")) | {m.uid} == {"GALA|t1|1", "GALA|t2|7", "GALB|t2|3"}
    assert "GALA" in m.also_in
    # same tile, same galaxy, within 4": NOT merged (the pipeline already grouped them)
    df2 = df.iloc[[0, 3]].assign(ra=[10.0, 10.0 + d])
    assert len(mt.merge_candidates(df2, targets())) == 2


def _row(**kw):
    base = dict(cls="not-variable", gate_band=1, lc_w1_recovery=0.0, lc_w2_recovery=0.0)
    base.update(kw)
    return pd.Series(base)


def test_triage_classes():
    assert mt.triage_class(_row(cls="step-down")) == "failed-SN-like"
    assert mt.triage_class(_row(cls="rise-then-fade")) == "failed-SN-like"
    assert mt.triage_class(_row(cls="transient")) == "obscured-transient"
    assert mt.triage_class(_row(cls="step-up")) == "step-up"
    for c in ("lpv-like", "irregular", "season-locked"):
        assert mt.triage_class(_row(cls=c)) == "demoted"
    assert mt.fsn_shape(_row(cls="fading", lc_w1_recovery=0.1)) == "fade-no-recovery"
    assert mt.fsn_shape(_row(cls="fading", lc_w1_recovery=0.6)) == "fading-recovering"


def _score_frame(n=3, **cols):
    base = dict(cls=["step-down"] * n, triage_class=["failed-SN-like"] * n, fsn_shape=["step-down"] * n,
                w1_delta_late_sig=[-6.0] * n, w2_delta_late_sig=[-4.0] * n, w1_delta_neo_sig=[-7.0] * n,
                w2_delta_neo_sig=[-6.0] * n, w1_rise_sig=[np.nan] * n, w2_rise_sig=[np.nan] * n,
                w1_fade_sig=[np.nan] * n, w2_fade_sig=[np.nan] * n, Lbol_pre_est=[1e5] * n, depth_w1=[0.8] * n,
                depth_w2=[0.8] * n, colour_fade=[0.5] * n, colour_up=[np.nan] * n, dipole=[False] * n)
    base.update(cols)
    return pd.DataFrame(base)


def test_fsn_score_factors():
    # the h0012a (v1) score, kept as fsn_score_v1; v2 is tested in test_h0012_v2.py
    df = _score_frame(4, Lbol_pre_est=[1e5, 1e2, 1e5, 1e5], dipole=[False, False, True, False],
                      gaia_foreground=[False, False, False, True])
    s = mt.fsn_score_v1(df)
    assert s[0] > 0
    assert s[1] < 0.01 * s[0]  # 1e2 L_sun: far below the RSG window
    assert s[2] == pytest.approx(0.1 * s[0])  # dipole
    assert s[3] == pytest.approx(0.02 * s[0])  # Gaia foreground star
    df = _score_frame(2, triage_class=["failed-SN-like", "demoted"])
    assert mt.fsn_score_v1(df)[1] == 0
    assert mt.fsn_score(df)[1] == 0


def test_obs_score_prefers_luminous_red_uncatalogued():
    n = 3
    df = pd.DataFrame(dict(cls=["transient"] * n, triage_class=["obscured-transient"] * n,
                           w1_rise_sig=[20.0] * n, w2_rise_sig=[20.0] * n, w1_delta_late_sig=[0.0] * n,
                           w2_delta_late_sig=[0.0] * n, w1_delta_neo_sig=[0.0] * n, w2_delta_neo_sig=[0.0] * n,
                           lc_w1_burst_sig=[0.0] * n, lc_w2_burst_sig=[0.0] * n,
                           L_peak=[1e6, 1e4, 1e6], colour_up=[1.0, 1.0, 0.0],
                           gaia_status=["ok"] * n, gaia_id=pd.array([pd.NA, pd.NA, "123"], dtype="string"),
                           known=[False] * n))
    s = mt.obs_score(df)
    assert s[0] > s[1] and s[0] > s[2]
    assert s[0] == pytest.approx(20 / 5 * 1 * 2 * 1.5)


def test_parse_tns_csv_and_html_is_error():
    text = ('"ID","Name","RA","DEC","Obj. Type","Discovery Date (UT)"\n'
            '"20473","SN 2017eaw","20:34:44.240","+60:11:35.84","SN II","2017-05-14 05:42:43.000"\n')
    d = mt.parse_tns_csv(text)
    assert d.Name.iloc[0] == "SN 2017eaw"
    assert d.ra.iloc[0] == pytest.approx(308.684333, abs=1e-5)
    assert d.dec.iloc[0] == pytest.approx(60.193289, abs=1e-5)
    with pytest.raises(ValueError):
        mt.parse_tns_csv("<html>Just a moment...</html>")
    assert mt.parse_tns_csv("").empty


class _Resp:
    def __init__(self, code, text="", headers=None):
        self.status_code, self.text, self.headers = code, text, headers or {}


def test_tns_429_is_an_error_never_nothing(monkeypatch):
    monkeypatch.setattr(mt.time, "sleep", lambda s: None)
    calls = []

    def get(p):
        calls.append(p)
        return _Resp(429, headers={"Retry-After": "1"})

    cone = dict(key="tns_X", ra=1.0, dec=2.0, r_arcmin=3.0, members=["X"])
    objs, st = mt.tns_cone(cone, get=get)
    assert st.startswith("ERR") and "429" in st
    assert objs.empty and len(calls) == 5
    # not cached as 'ok': a later call queries again, and cache-only mode says "not queried"
    assert mt.tns_cone(cone, fetch=False)[1] == "not queried"
    ok_text = '"ID","Name","RA","DEC","Obj. Type"\n'
    objs, st = mt.tns_cone(cone, get=lambda p: _Resp(200, ok_text))
    assert st == "ok" and objs.empty
    assert mt.tns_cone(cone, fetch=False)[1] == "ok"  # now cached


def test_tns_paginates(monkeypatch):
    monkeypatch.setattr(mt, "TNS_PAGE", 2)
    head = '"ID","Name","RA","DEC","Obj. Type"\n'
    rows = ['"1","AT 1","00:00:01.0","+01:00:00.0",""\n', '"2","AT 2","00:00:02.0","+01:00:00.0",""\n',
            '"3","AT 3","00:00:03.0","+01:00:00.0",""\n']
    pages = {0: head + rows[0] + rows[1], 1: head + rows[2]}
    objs, st = mt.tns_cone(dict(key="tns_P", ra=0, dec=1, r_arcmin=1, members=["P"]),
                           get=lambda p: _Resp(200, pages[p["page"]]))
    assert st == "ok" and list(objs.Name) == ["AT 1", "AT 2", "AT 3"]


def test_match_known_and_identify():
    df = pd.DataFrame(dict(galaxy=["NGC6946", "NGC6946", "NGC6946"], ra=[308.684169, 308.8650, 308.70],
                           dec=[60.193307, 60.13573, 60.15], cls=["transient", "step-down", "transient"]))
    tns = {"NGC6946": (pd.DataFrame(dict(Name=["SN 2017eaw"], ra=[308.684333], dec=[60.193289],
                                         **{"Obj. Type": ["SN II"], "Discovery Date (UT)": ["2017-05-14"]})), "ok")}
    out = mt.identify(mt.match_known(df, tns))
    assert out.known.tolist() == [True, True, False]
    assert out.known_name.tolist()[:2] == ["SN 2017eaw", "N6946-BH1"]
    assert out.what.iloc[2] == "unknown"
    # a failed TNS lookup is reported as such, not as 'no match'
    out2 = mt.match_known(df.copy(), {"NGC6946": (pd.DataFrame(), "ERR HTTP 429")})
    assert set(out2.tns_status) == {"ERR HTTP 429"}


def test_tns_cones_cover_every_target():
    t = mt.load_targets()
    cones = mt.tns_cones(t)
    members = [g for c in cones for g in c["members"]]
    assert sorted(members) == sorted(t.Name)
    for c in cones:
        for g in c["members"]:
            s = mt.sep_arcsec(c["ra"], c["dec"], t.loc[g].ra, t.loc[g].dec) / 60
            assert s + t.loc[g].search_diam_arcmin / 2 <= c["r_arcmin"] + 1e-6
