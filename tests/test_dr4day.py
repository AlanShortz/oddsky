"""Gaia DR4-day pipeline (oddsky.dr4day, hunt H-0014). Offline: archive calls are faked."""
from __future__ import annotations

from pathlib import Path

import httpx
import numpy as np
import pandas as pd
import pytest

from oddsky.analysis.lensing import magnification
from oddsky.data import gaia_epoch
from oddsky.dr4day import archive as A
from oddsky.dr4day import catalogue, config, idfix, lightcurves, probe, readiness, targets

ROOT = Path(__file__).resolve().parents[1]


# ---- config: one switch ---------------------------------------------------------------------------------------------
def test_release_presets_and_overrides(monkeypatch):
    monkeypatch.delenv("ODDSKY_GAIA_RELEASE", raising=False)
    assert config.release().key == "dr3"
    dr4 = config.release("dr4")
    assert dr4.name == "Gaia DR4" and dr4.schema == "gaiadr4" and not dr4.stand_in
    assert dr4.table("vari_microlensing") == "gaiadr4.vari_microlensing"
    assert dr4.neighbourhood[:3] == ("gaiadr4.dr3_neighbourhood", "dr3_source_id", "source_id")
    assert dr4.classifier_cols == ("classifier_best_class_name", "classifier_best_class_prob")
    assert dr4.in_span(58800) and not config.release("dr3").in_span(58800)
    monkeypatch.setenv("ODDSKY_GAIA_RELEASE", "Gaia DR4")
    assert config.release().key == "dr4"
    r = config.release("dr4", config.parse_overrides(["tables.vari_microlensing=gaiadr4.vml", "chunk=10", "pause_s=0.5",
                                                      "stand_in=true", "classifier_cols=a,b"]))
    assert (r.table("vari_microlensing"), r.chunk, r.pause_s, r.stand_in, r.classifier_cols) == \
        ("gaiadr4.vml", 10, 0.5, True, ("a", "b"))
    with pytest.raises(ValueError):
        config.release("dr4", {"nonsense": "1"})
    with pytest.raises(ValueError):
        config.release("dr9")
    with pytest.raises(ValueError):
        config.parse_overrides(["novalue"])


# ---- gaia_epoch: DR3 unchanged, DR4 draft layout readable -----------------------------------------------------------
def _dr3_raw():
    return pd.DataFrame({
        "source_id": [7, 7, 7], "transit_id": [11, 12, 13], "g_transit_time": [1710.0, 1720.0, 1730.0],
        "g_transit_mag": [15.0, 15.1, 14.0], "g_transit_flux_over_error": [100.0, 100.0, 0.0],
        "bp_obs_time": [1710.0, 1720.0, 1730.0], "bp_mag": [15.5, np.nan, 14.5], "bp_flux_over_error": [50.0, 50.0, 50.0],
        "rp_obs_time": [1710.0, 1720.0, 1730.0], "rp_mag": [14.5, 14.6, 13.5], "rp_flux_over_error": [80.0, 80.0, 80.0],
        "rejected_by_photometry": ["false", "true", "false"], "variability_flag_g_reject": ["false", "false", "true"],
        "variability_flag_bp_reject": ["false"] * 3, "variability_flag_rp_reject": ["false"] * 3})


def test_to_series_dr3_layout_unchanged():
    df = gaia_epoch.to_series(_dr3_raw())
    g = df[df.band == "G"].reset_index(drop=True)
    assert list(g.t_mjd) == [1710.0 + 55197.0, 1720.0 + 55197.0, 1730.0 + 55197.0]
    assert list(g.flag) == ["", "rejected_by_photometry", "rejected_by_variability"]
    assert g.err.iloc[0] == pytest.approx(1.0857 / 100) and g.err.iloc[2] == 0.05  # non-positive flux/error -> 0.05
    assert len(df[df.band == "BP"]) == 2  # the NaN BP magnitude is dropped by series.normalize
    assert set(df.camera) == {"11", "12", "13"}


def test_to_series_dr4_draft_layout():
    raw = _dr3_raw().rename(columns={"g_transit_time": "g_obs_time", "g_transit_mag": "g_mag",
                                     "g_transit_flux_over_error": "g_flux_over_error"})
    raw = raw.drop(columns=["rejected_by_photometry", "variability_flag_g_reject", "variability_flag_bp_reject",
                            "variability_flag_rp_reject"])
    assert gaia_epoch.column_map(raw)[0] == "dr4"
    df = gaia_epoch.to_series(raw)
    assert (df.flag == "").all()  # DR4 epoch_photometry carries no rejection flags
    assert len(df[df.band == "G"]) == 3 and len(df[df.band == "BP"]) == 2
    with pytest.raises(KeyError, match="g_transit_time"):
        gaia_epoch.column_map(raw.drop(columns=["g_obs_time"]))


# ---- idfix: float-corrupted ids --------------------------------------------------------------------------------------
def test_recover_float_ids():
    true = 4756341994426711123
    f = repr(float(true))
    a, b = idfix.window(f)
    assert a <= true <= b
    cands = pd.DataFrame({"source_id": [str(true), str(true + 7)], "ra": [10.0, 10.0], "dec": [-5.0, -5.0001],
                          "phot_g_mean_mag": [15.00, 17.0]})
    rows = pd.DataFrame({"id": ["T1", "T2", "T3"], "float_id": [f, None, repr(float(1234567890123456789))],
                         "ra": [10.0, 1.0, 1.0], "dec": [-5.0, 1.0, 1.0], "gaia_g": [15.005, 12.0, 12.0]})
    m = idfix.match(cands, rows)
    assert m.source_id.tolist() == [str(true), "", ""]
    assert m.reason.tolist()[1:] == ["no Gaia id listed", "no source in the id window"]
    assert "BETWEEN" in idfix.query([(1, 2)])


# ---- archive: politeness and error recording ------------------------------------------------------------------------
def _arc(handler, rel=None):
    rel = rel or config.release("dr3", {"pause_s": "0"})
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return A.Archive(rel, client=client, login=False, sleep=lambda s: None, backoff_s=0)


def test_archive_retries_5xx_then_succeeds_and_never_retries_4xx():
    calls = []

    def h(req):
        calls.append(1)
        return httpx.Response(503, text="busy") if len(calls) < 2 else httpx.Response(200, text="source_id,x\n123456789012345678,1\n")
    d = _arc(h).tap("SELECT 1", sync=True)
    assert len(calls) == 2 and d.source_id.iloc[0] == "123456789012345678"  # ids stay strings

    # a refused sync job goes async: submit, poll the phase, fetch the result
    def busy_sync(req):
        u = str(req.url)
        if u.endswith("/sync"):
            return httpx.Response(503, text="<b>Message: </b>maximum number of synchronous queued jobs</li>")
        if u.endswith("/async"):  # the TAP service answers a new job with a redirect to the job's URL
            return httpx.Response(303, headers={"Location": u + "/J1"})
        if u.endswith("/J1"):
            return httpx.Response(200, text="<job/>")
        if u.endswith("/phase"):
            return httpx.Response(200, text="COMPLETED")
        return httpx.Response(200, text="source_id\n42\n")
    rel = config.release("dr3", {"pause_s": "0"})
    arc = A.Archive(rel, client=httpx.Client(transport=httpx.MockTransport(busy_sync), follow_redirects=True), login=False,
                    sleep=lambda s: None, backoff_s=0)
    assert arc.tap("SELECT 1", sync=True).source_id.tolist() == ["42"]

    def weird_phase(req):
        return httpx.Response(200, text="<html>maintenance</html>") if str(req.url).endswith("/phase") else \
            httpx.Response(200, text="x")
    with pytest.raises(A.ArchiveError, match="unexpected phase"):
        _arc(weird_phase).tap("SELECT 1")

    def h400(req):
        calls.append(1)
        return httpx.Response(400, text="bad query")
    calls.clear()
    with pytest.raises(A.ArchiveError):
        _arc(h400).tap("SELECT nonsense", sync=True)
    assert len(calls) == 1


def test_epoch_chunk_failure_is_an_error_not_an_empty_result(tmp_path):
    raw = _dr3_raw()

    def h(req):
        ids = dict(httpx.QueryParams(req.content.decode()))["ID"].split(",")
        if "999999" in ids:
            return httpx.Response(503, text="<b>Message: </b>overloaded</li>")
        rows = raw[raw.source_id.astype(str).isin(ids)]
        return httpx.Response(200, text=rows.to_csv(index=False))
    arc = _arc(h, config.release("dr3", {"pause_s": "0", "chunk": "2"}))
    got, recs = arc.epoch(["7", "8", "999999"], cache=tmp_path)
    assert set(got) == {"7"}
    assert recs[0]["ok"] and recs[0]["n_returned"] == 1  # "8" asked, absent: not an error
    assert not recs[1]["ok"] and recs[1]["ids"] == ["999999"] and "overloaded" in recs[1]["error"]
    assert arc.errors and arc.errors[0]["where"] == "epoch_photometry"
    assert (tmp_path / "7.csv").exists()
    got2, recs2 = arc.epoch(["7"], cache=tmp_path)  # cached: no request
    assert set(got2) == {"7"} and recs2 == []


def test_links_parses_retrieval_types_and_faults():
    vot = ('<?xml version="1.0"?><VOTABLE xmlns="http://www.ivoa.net/xml/VOTable/v1.4"><RESOURCE><TABLE>'
           '<FIELD name="ID"/><FIELD name="access_url"/><FIELD name="error_message"/><DATA><TABLEDATA>'
           '<TR><TD>x</TD><TD>https://a/data?ID=x&amp;RETRIEVAL_TYPE=EPOCH_PHOTOMETRY&amp;L=1</TD><TD></TD></TR>'
           '<TR><TD>x</TD><TD>https://a/data?ID=x&amp;RETRIEVAL_TYPE=EPOCH_ASTROMETRY</TD><TD></TD></TR>'
           '</TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>')
    r = _arc(lambda req: httpx.Response(200, text=vot)).links("1")
    assert r == {"retrieval_types": ["EPOCH_ASTROMETRY", "EPOCH_PHOTOMETRY"], "faults": []}


def test_probe_reports_unknown_epoch_layout():
    class Fake:
        logged_in, chunk = False, 50

        def tap(self, q, sync=False):
            if "tap_schema.tables" in q:
                return pd.DataFrame({"table_name": list(config.release("dr4").tables.values())})
            if "tap_schema.columns" in q:
                return pd.DataFrame({"column_name": ["source_id"]})
            return pd.DataFrame({"cls": ["MICROLENSING"]})

        def links(self, s):
            return {"retrieval_types": ["EPOCH_PHOTOMETRY"], "faults": []}

        def epoch_raw(self, ids):
            return [pd.DataFrame({"source_id": ["1"], "transit_id": [1], "weird_time": [1.0]})]

    out = probe.run(Fake(), config.release("dr4"))
    assert not out["ok"] and out["epoch"]["layout"] is None
    assert any("COLUMN_MAPS" in f for f in out["fixes"])
    assert any("classifier_best_class_name" in f for f in out["fixes"])


# ---- light curves ---------------------------------------------------------------------------------------------------
def _lc(fG, fBP=None, fRP=None, n=150, seed=1, t=None):
    rng = np.random.default_rng(seed)
    t = np.sort(rng.uniform(56870, 58860, n)) if t is None else t
    rows = []
    for band, f, m0, e in (("G", fG, 16.0, 0.01), ("BP", fBP or fG, 16.6, 0.02), ("RP", fRP or fG, 15.3, 0.015)):
        mag = m0 - 2.5 * np.log10(f(t)) + rng.normal(0, e, len(t))
        rows.append(pd.DataFrame(dict(t_mjd=t, mag=mag, err=e, band=band, survey="GAIA", flag="",
                                      camera=[str(i) for i in range(len(t))])))
    return pd.concat(rows, ignore_index=True)


def _lens(t0=57800.0, te=40.0, u0=0.2):
    return lambda t: magnification(np.hypot((t - t0) / te, u0))


def test_lens_is_lens_like_and_achromatic():
    t = np.sort(np.r_[np.random.default_rng(3).uniform(56870, 58860, 120), 57770 + np.arange(0, 60, 6.0)])
    a = lightcurves.analyse(_lc(_lens(), t=t), 270.0, -30.0, t_event=57801.0)
    assert a["label"] == "lens-like brightening"
    assert a["colour"] == "achromatic"
    assert abs(a["lens_t0"] - 57800) < 10 and 20 < a["lens_tE"] < 80
    assert a["ev_status"] == "pass"  # the sealed ensemble rule, imported unchanged, agrees


def test_chromatic_bump_and_decline_and_quiet():
    t = np.sort(np.r_[np.random.default_rng(4).uniform(56870, 58860, 120), 57770 + np.arange(0, 60, 6.0)])
    bump = lambda amp: (lambda tt: 1 + amp * np.exp(-0.5 * ((tt - 57800) / 15) ** 2))  # noqa: E731
    a = lightcurves.analyse(_lc(bump(1.0), fBP=bump(2.5), fRP=bump(0.5), t=t), fit=False)
    assert a["colour"] == "chromatic" and "chromatic brightening" in a["label"]
    dip = lambda tt: np.where((tt > 57500) & (tt < 57600), 10 ** (-0.4 * 2.0), 1.0)  # noqa: E731
    d = lightcurves.analyse(_lc(dip, t=np.sort(np.r_[t, 57510 + np.arange(0, 80, 8.0)])), fit=False)
    assert "deep decline" in d["label"] and d["dG_fade"] > 1.5
    mira = lambda tt: 10 ** (-0.4 * 1.5 * np.sin(2 * np.pi * tt / 330.0))  # noqa: E731  a 3-mag, 330-d Mira
    mi = lightcurves.analyse(_lc(mira), fit=False)
    assert mi["label"].endswith("periodic large-amplitude variable") and abs(mi["ls_period"] - 330) < 15
    q = lightcurves.analyse(_lc(lambda tt: np.ones_like(tt)), fit=False)
    assert q["label"] == "quiet"
    assert lightcurves.analyse(_lc(lambda tt: np.ones_like(tt), n=5))["label"] == "too few G transits"
    assert lightcurves.priority("lens-like brightening", "pass") < lightcurves.priority("lens-like brightening") < \
        lightcurves.priority("quiet")


# ---- readiness ------------------------------------------------------------------------------------------------------
def test_span_status_and_provisional():
    from oddsky.case.model import Check
    dr4, dr3 = config.release("dr4"), config.release("dr3")
    later = Check(series="GAIA:G", start=59611, end=60096, statistic="brightest", baseline=[57023, 59580], op="<", value=-1.2)
    early = Check(series="GAIA:G", start=57949, end=58042, statistic="median", baseline=[56863.5, 57570], op="<", value=-1.2)
    assert readiness.span_status(later, dr4).startswith("window after")
    assert readiness.span_status(early, dr4) == "inside"
    assert readiness.span_status(early, dr3).startswith("window after")
    t = np.r_[np.linspace(56900, 57500, 20), np.linspace(57960, 58030, 6)]
    g = pd.DataFrame(dict(t_mjd=t, mag=np.r_[np.full(20, 18.3), np.full(6, 16.5)], err=0.02, band="G", flag=""))
    p = readiness.provisional(early, g)
    assert p["outcome"] == "true" and p["observed"] == pytest.approx(-1.8)
    assert readiness.provisional(early, None)["outcome"] == "unresolvable"


def test_readiness_flags_fallback_and_never_writes(tmp_path):
    from oddsky.case.model import Case, Check, Prediction, Target
    from oddsky.case.store import CaseStore
    (tmp_path / "cases" / "OS-9999").mkdir(parents=True)
    s = CaseStore(tmp_path / "cases" / "OS-9999")
    chk = Check(series="GAIA:G", start=57949, end=58042, statistic="median", baseline=[56863.5, 57570], op="<", value=-1.2)
    s.save(Case(id="OS-9999", title="t", target=Target(name="x", ra=1.0, dec=2.0, gaia_source_id="42"),
                predictions=[Prediction(id="P1", statement="s", check=chk, probability=0.9)]))
    s.write_context({"gaia": {"G": 18.3}})
    before = (tmp_path / "cases" / "OS-9999" / "case.yaml").read_text()
    t = np.r_[np.linspace(56900, 57500, 20), np.linspace(57960, 58030, 6)]
    df = pd.DataFrame(dict(t_mjd=t, mag=np.r_[np.full(20, 18.3), np.full(6, 16.5)], err=0.02, band="G", flag=""))

    def fetch(ids, releases):  # DR4 fails, DR3 answers: the case the hosted grader would grade on old data
        return {42: df}, {"releases": [{"release": "Gaia DR4", "ok": False, "error": "500"},
                                       {"release": "Gaia DR3", "ok": True, "error": ""}], "source_release": {42: "Gaia DR3"}}
    rows, failed = readiness.check(config.release("dr4"), fetch=fetch, root=tmp_path)
    assert failed and rows[0]["fallback"] and rows[0]["provisional"] == "true" and rows[0]["identity_ok"]
    assert "HOLD THE GRADER" in readiness.summary(rows, failed, config.release("dr4"))
    assert (tmp_path / "cases" / "OS-9999" / "case.yaml").read_text() == before


# ---- catalogue ------------------------------------------------------------------------------------------------------
def test_idmap_rule_nearest_within_limits():
    nb = pd.DataFrame({"old_id": ["1", "1", "2", "3"], "new_id": ["10", "11", "20", "30"],
                       "dist_mas": [300.0, 20.0, 800.0, 10.0], "dmag": [0.0, 0.1, 0.0, 0.5]})
    m = catalogue.idmap_rule(nb, ["1", "2", "3", "4"]).set_index("dr3_source_id")
    assert m.new_source_id.to_dict() == {"1": "11", "2": "2", "3": "3", "4": "4"}


def test_crossmatch_separates_catalogued_reference_and_unreported():
    tg = pd.DataFrame({"source_id": ["1", "2"], "set": ["strong", "h0010"], "tier": [1, 1], "name": ["a", "b"],
                       "ra": [10.0, 20.0], "dec": [0.0, 0.0], "t_event": [57000.0, np.nan], "note": ["", ""]})
    cat = pd.DataFrame({"source_id": ["2", "3", "4"], "ra": [20.0, 30.0, 40.0], "dec": [0.0, 0.0, 0.0],
                        "tmax_mjd": [57100.0, 57200.0, 57300.0]})
    ref = pd.DataFrame({"name": ["OGLE-x", "KMT-y"], "ra": [10.0, 30.0], "dec": [0.0, 0.0], "t0_mjd": [57010.0, 57210.0],
                        "tE": [20.0, 20.0], "source": ["OGLE", "KMT"]})
    nw = pd.DataFrame({"designation": ["Jx"], "ra": [40.0], "dec": [0.0], "t": [57290.0], "dw1": [-1.0], "dw2": [-1.0],
                       "class": ["unclassified"]})
    per, new = catalogue.crossmatch(tg, cat, None, ref, nw)
    assert per.in_release_lens_catalogue.tolist() == [False, True]
    assert per.reference_lens.iloc[0].startswith("OGLE-x")
    assert new.source_id.tolist() == ["3", "4"]
    assert new.unreported.tolist() == [False, True] and new.neowise_event.iloc[1].startswith("Jx")


# ---- targets (reads the repo's own hunt files) ----------------------------------------------------------------------
def test_targets_from_repo(monkeypatch):
    monkeypatch.chdir(ROOT)
    t = targets.build(ROOT, tiers=(1,))
    n = t.groupby("set").size()
    assert n["strong"] + n["nogaia"] == 118 and n["h0010"] == 67 and n["sealed"] >= 9
    assert (t[t.set != "nogaia"].source_id.str.len() >= 15).all()  # ids kept as strings, not floats
    assert t[t.set == "nogaia"].t_event.lt(58869).sum() == 11  # the ensemble's 11 events without a DR3 star
    assert t[t.set == "h0010"].t_event.isna().all()  # Gaia's own peak is not an independent event time


def test_vsx_parse_and_errors_are_recorded():
    text = ("#\n#   VizieR Astronomical Server vizier.idia.ac.za\n#\n_r\tName\tType\narcsec\t\t\n-----\t----\t----\n"
            " 0.05\tASASSN-V J161156.22-575527.2  \tRCB\n 6.10\tNSV 1\tL\n")

    class R:
        def __init__(self, t):
            self.text = t

        def raise_for_status(self):
            pass

    rows = pd.DataFrame({"release_source_id": ["1", "2", "3"], "ra": [242.98, 10.0, np.nan], "dec": [-57.9, 1.0, np.nan]})
    calls = iter([R(text), RuntimeError("timeout")])

    def get(params):
        x = next(calls)
        if isinstance(x, Exception):
            raise x
        return x
    errs = []
    v = catalogue.vsx(rows, pause_s=0, get=get, on_error=lambda w, m: errs.append(m)).set_index("release_source_id").vsx
    assert v["1"] == 'ASASSN-V J161156.22-575527.2 RCB 0.1"; NSV 1 L 6.1"'
    assert v["2"].startswith("error: RuntimeError") and v["3"] == "error: no position" and len(errs) == 1


def test_priority_demotes_other_variable_classes():
    assert lightcurves.priority("lens-like brightening", other_class=True) == lightcurves.priority("lens-like brightening") + 2
