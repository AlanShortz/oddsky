"""The Tonight page: its data comes from the case files (site/build.py: build_tonight), and its rise-and-set
arithmetic (web/js/skycalc.js) is checked against astropy."""

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("site_build", ROOT / "site" / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
node = shutil.which("node")


def _series(t, mag, unit="mag"):
    return {"t": t, "mag": mag, "unit": unit}


def _cases():
    star = {"case": {"id": "OS-1", "title": "A star", "target": {"name": "T Tst", "ra": 10.0, "dec": 20.0},
                     "claims": [{"id": "C7", "text": "Eclipses phase up on P = 2.5 d (T0 = MJD 60000.25)."}],
                     "predictions": [
                         {"id": "P1", "statement": "fades", "probability": 0.7, "resolve_by": "2027-09-01",
                          "check": {"series": "AAVSO:V", "start": 61000.0, "end": 61100.0, "baseline": [60980.0, 60995.0], "statistic": "median", "op": ">", "value": 13.0}},
                         {"id": "P2", "statement": "gaia", "probability": 0.6, "check": {"series": "GAIA:G", "start": 57000.0, "end": 58000.0}},
                         {"id": "P3", "statement": "done", "probability": 0.5, "resolution": {"outcome": "true"},
                          "check": {"series": "AAVSO:V", "start": 60000.0, "end": 60100.0}}]},
            "series": {"AAVSO:V": _series([60990.0, 61010.0, 61050.0], [12.9, 13.0, 13.1]), "AAVSO:B": _series([61060.0], [14.0]),
                       "AAVSO:N/A": _series([61070.0], [9.0]), "NEOWISE:W1": _series([61080.0], [8.0]), "TESS:TESS": _series([61090.0], [1.0], "rel")},
            "provenance": {"aavso": {"retrieved_at": "2026-01-20T05:00:00+00:00", "rows_kept": 100,
                                     "notes": ["observers (good points): ABC:30, DEF:10", "something else"]}}}
    control = {"case": {"id": "OS-2", "title": "Control A", "target": {"name": "c", "ra": 1.0, "dec": 2.0}}, "series": {"AAVSO:V": _series([61000.0], [10.0])}}
    faint = {"case": {"id": "OS-3", "title": "Too faint", "target": {"name": "f", "ra": 1.0, "dec": 2.0}}, "series": {"ZTF:ZTF_r": _series([61000.0], [19.0])}}
    space = {"case": {"id": "OS-4", "title": "Space only", "target": {"name": "s", "ra": 1.0, "dec": 2.0}}, "series": {"GAIA:G": _series([61000.0], [12.0])}}
    idle = {"case": {"id": "OS-5", "title": "Survey star, nothing asked", "target": {"name": "i", "ra": 1.0, "dec": 2.0}}, "series": {"ATLAS:ATLAS_o": _series([61000.0], [14.0])}}
    return {"OS-1": star, "OS-2": control, "OS-3": faint, "OS-4": space, "OS-5": idle}


def test_only_reachable_ground_observed_stars_are_listed():
    tn = build.build_tonight({}, _cases(), {}, now_mjd=61100.0)
    assert [x["case"] for x in tn["targets"]] == ["OS-1"]      # not the control, the faint one, the space-only one or the idle one


def test_numbers_come_from_the_case_and_a_v_band_point_is_preferred_when_fresh():
    x = build.build_tonight({}, _cases(), {"OS-1": {"aavso": "T Tst", "bands": "V", "cadence": "weekly", "settles": "something"}}, now_mjd=61100.0)["targets"][0]
    # B is 10 days newer; V wins within 30. The archive-read date comes with it: "last measured" is our copy, not the sky.
    assert x["latest"] == {"series": "AAVSO:V", "mjd": 61050.0, "date": "2026-01-10", "mag": 13.1, "archive_read": "2026-01-20"}
    assert x["typical_mag"] == 13.0 and x["typical_band"] == "V"          # one band, not a mix of filters
    assert x["aavso"] == "T Tst" and x["ask"]["settles"] == "something"
    # the share is of all good points (rows_kept), not of the observers the note happens to list
    assert x["observers"] == {"listed": 2, "more": False, "top": "ABC", "top_points": 30, "points": 100, "top_share": 0.3}


def test_a_star_with_an_aavso_record_is_filed_under_its_name_and_others_are_not():
    targets = build.build_tonight({}, _cases(), {"OS-5": {"bands": "V", "cadence": "weekly", "settles": "x"}}, now_mjd=61100.0)["targets"]
    by = {x["case"]: x for x in targets}
    assert by["OS-1"]["aavso"] == "T Tst" and by["OS-5"]["aavso"] is None


def test_an_ephemeris_must_be_in_the_claim_it_cites():
    ok = {"OS-1": {"settles": "x", "ephemeris": {"period_d": 2.5, "t0_mjd": 60000.25, "claim": "C7", "what": "eclipse"}}}
    assert build.build_tonight({}, _cases(), ok, now_mjd=61100.0)["targets"][0]["ephemeris"]["period_d"] == 2.5
    bad = {"OS-1": {"settles": "x", "ephemeris": {"period_d": 2.6, "t0_mjd": 60000.25, "claim": "C7", "what": "eclipse"}}}
    with pytest.raises(ValueError):
        build.build_tonight({}, _cases(), bad, now_mjd=61100.0)


def test_only_pending_predictions_checked_on_ground_photometry_are_judged_here():
    x = build.build_tonight({}, _cases(), {}, now_mjd=61100.0)["targets"][0]
    assert [j["id"] for j in x["judged"]] == ["P1"]
    j = x["judged"][0]
    assert j["amateur"] and j["band"] == "V" and j["in_window"] == 2 and j["window"] == ["2025-11-21", "2026-03-01"]
    assert j["baseline"] == ["2025-11-01", "2025-11-16"] and j["in_baseline"] == 1      # the window it is compared with needs data too


def test_the_live_casebook_has_predictions_graded_on_amateur_photometry():
    index, cases = build.load_cases()
    asks = json.loads((ROOT / "site" / "tonight.json").read_text())["asks"]
    tn = build.build_tonight(index, cases, asks)
    assert set(asks) <= set(cases), "an ask names a case that does not exist"
    judged = [j for x in tn["targets"] for j in x["judged"] if j["amateur"]]
    assert judged and all(j["survey"] == "AAVSO" for j in judged)
    assert all(x["latest"]["mag"] < 25 and -90 <= x["dec"] <= 90 for x in tn["targets"])
    assert all(x["ask"] or x["judged"] or x["has_aavso_record"] for x in tn["targets"])      # nothing listed without a reason
    assert all(0 < x["observers"]["top_share"] <= 1 for x in tn["targets"] if x["observers"])
    md = build.tonight_markdown(tn)
    assert md.startswith("# Tonight") and all(x["case"] in md for x in tn["targets"])


@pytest.mark.skipif(not node, reason="node not installed")
def test_altitudes_agree_with_astropy_to_half_a_degree():
    import astropy.units as u
    from astropy.coordinates import AltAz, EarthLocation, SkyCoord, get_sun
    from astropy.time import Time

    cases = [(295.4879, 16.7444, 40.0, -75.0, "2026-11-11T02:00:00"), (123.8471, -38.9898, -33.0, 151.0, "2027-02-01T13:30:00"),
             (332.3448, 55.7567, 52.0, 0.0, "2031-06-20T23:00:00"), (68.7309, 24.4814, 0.0, 100.0, "2026-12-25T16:00:00")]
    script = ("import(process.argv[1]).then((m) => console.log(JSON.stringify(JSON.parse(process.argv[2]).map(([ra, dec, lat, lon, iso]) => {"
              "const jd = m.jdOf(new Date(iso + 'Z')); const s = m.sunRaDec(jd);"
              "return [m.altitude(ra, dec, lat, lon, jd), m.altitude(s.ra, s.dec, lat, lon, jd)]; }))));")
    out = subprocess.run([node, "--input-type=module", "-e", script, (ROOT / "web/js/skycalc.js").as_uri(), json.dumps(cases)],
                         capture_output=True, text=True, check=True).stdout
    for (ra, dec, lat, lon, iso), (alt, sun_alt) in zip(cases, json.loads(out), strict=True):
        frame = AltAz(obstime=Time(iso), location=EarthLocation(lat=lat * u.deg, lon=lon * u.deg))
        assert abs(alt - SkyCoord(ra * u.deg, dec * u.deg).transform_to(frame).alt.deg) < 0.5
        assert abs(sun_alt - get_sun(Time(iso)).transform_to(frame).alt.deg) < 0.5


@pytest.mark.skipif(not node, reason="node not installed")
def test_a_night_has_darkness_and_a_southern_star_never_rises_in_the_north():
    script = ("import(process.argv[1]).then((m) => { const d = new Date('2026-11-11T02:00:00Z');"
              "const n = m.night(295.4879, 16.7444, 40, -75, d);"
              "console.log(JSON.stringify([n.hoursDark, n.hoursUp, n.best.alt, m.everUp(-76.2, 50), m.everUp(16.7, 40), m.season(295.4879, 16.7444, 40, -75, 2026)])); });")
    dark, up, best, south, north, season = json.loads(subprocess.run(
        [node, "--input-type=module", "-e", script, (ROOT / "web/js/skycalc.js").as_uri()], capture_output=True, text=True, check=True).stdout)
    assert 10 < dark < 13 and 0 < up < dark and 30 <= best <= 67
    assert south is False and north is True
    assert 6 in season and 0 not in season          # a summer star from 40 N: up in July, behind the Sun in January


@pytest.mark.skipif(not node, reason="node not installed")
def test_a_morning_visitor_is_shown_the_night_to_come_and_eclipse_times_follow_the_ephemeris():
    script = ("import(process.argv[1]).then((m) => { const morning = new Date('2026-11-11T13:00:00Z');"
              "const n = m.night(295.4879, 16.7444, 40, -75, morning);"
              "const mins = m.nextMinima(60000.25, 2.5, new Date('2026-11-11T00:00:00Z'), 2).map((d) => d.getTime() / 86400000 + 40587);"
              "console.log(JSON.stringify([n.darkStart.getTime() > morning.getTime(), mins, m.monthRuns([0, 1, 2, 9, 10, 11]), m.monthRuns([2, 3, 4, 8]),"
              "m.night(295, 16, 70, 20, new Date('2026-06-21T12:00:00Z')).darkStart])); });")
    ahead, mins, wrap, split, polar = json.loads(subprocess.run(
        [node, "--input-type=module", "-e", script, (ROOT / "web/js/skycalc.js").as_uri()], capture_output=True, text=True, check=True).stdout)
    assert ahead is True and polar is None                      # midnight sun: no darkness to report
    assert wrap == [[9, 2]] and split == [[2, 4], [8, 8]]
    e = [(m - 60000.25) / 2.5 for m in mins]
    assert all(abs(x - round(x)) < 1e-6 for x in e) and mins[0] >= 61355.0 and mins[1] - mins[0] == pytest.approx(2.5)


@pytest.mark.skipif(not node, reason="node not installed")
def test_the_router_claims_the_page():
    script = "import(process.argv[1]).then(({ parseRoute }) => console.log(parseRoute('/tonight').name));"
    out = subprocess.run([node, "--input-type=module", "-e", script, (ROOT / "web/js/routes.js").as_uri()], capture_output=True, text=True, check=True).stdout
    assert out.strip() == "tonight"
