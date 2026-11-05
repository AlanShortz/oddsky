"""H-0016: the Skeptic's AllWISE profile-fit check (offline; the catalogue row is given, not fetched)."""
import numpy as np

from oddsky import skeptic
from oddsky.data import allwise
from oddsky.data.allwise import best_duplicate, diagnose, expected_w1snr
from oddsky.data.provenance import Provenance

GOOD = {"ra": 10.0, "dec": -20.0, "w1mpro": 12.5, "w1mag": 12.52, "w1snr": 46.8, "nb": 1, "w1mjdmean": 55400.0, "w1nm": 24, "w1m": 24}
# J234829.46-440418.4: w1mpro 12.72, w1mag 11.05, w1snr 8.2, AllWISE 0.9" off Gaia, images and NEOWISE at 10.99-11.07
BAD = {"ra": 10.0 + 0.9 / 3600 / np.cos(np.radians(-20.0)), "dec": -20.0, "w1mpro": 12.72, "w1mag": 11.05, "w1snr": 8.2,
       "nb": 1, "w1mjdmean": 55441.0, "w1nm": 20, "w1m": 28}


def test_expected_snr_is_flat_then_falls():
    assert abs(expected_w1snr(10.0) - 47.5) < 0.1
    assert 41 < expected_w1snr(14.0) < 42
    assert expected_w1snr(14.5) < expected_w1snr(13.0)


def test_diagnose_passes_a_normal_star_and_fails_the_h0016_artifact():
    gaia = {"ra": 10.0, "dec": -20.0, "pmra": 0.0, "pmdec": 0.0}
    ok = diagnose(GOOD, gaia)
    assert ok["verdict"] == "ok" and ok["tests_failed"] == 0 and ok["offset_from_gaia_arcsec"] < 0.05
    bad = diagnose(BAD, gaia)
    assert bad["verdict"] == "bad" and bad["tests_failed"] == 3  # the frame fraction (0.71) passes for this one
    assert abs(bad["aperture_minus_profile_w1"] + 1.67) < 0.01 and bad["offset_from_gaia_arcsec"] > 0.8


def test_proper_motion_is_propagated_to_the_allwise_epoch():
    # a star moving 500 mas/yr: between J2016.0 and 2010.6 it was 2.7" away; the AllWISE row sits there, so no offset
    pm = 500.0
    yrs = (55400.0 - 51544.5) / 365.25 + 2000.0 - 2016.0
    aw = dict(GOOD, dec=-20.0 + yrs * pm / 3.6e6)
    d = diagnose(aw, {"ra": 10.0, "dec": -20.0, "pmra": 0.0, "pmdec": pm})
    assert d["offset_from_gaia_arcsec"] < 0.05 and d["verdict"] == "ok"


def test_skeptic_reports_the_check(dusty_case):
    ctx = dusty_case.context()
    ctx["allwise"] = dict(BAD)
    ctx["gaia"].update({"ra": 10.0, "dec": -20.0, "pmra": 0.0, "pmdec": 0.0})
    dusty_case.write_context(ctx)
    rep = skeptic.run(dusty_case, write=False)
    c = [x for x in rep["checks"] if x["id"] == "allwise_fit"][0]
    assert c["status"] == "fail" and "profile-fit failure" in c["finding"]
    ctx["allwise"] = dict(GOOD)
    dusty_case.write_context(ctx)
    rep = skeptic.run(dusty_case, write=False)
    assert [x for x in rep["checks"] if x["id"] == "allwise_fit"][0]["status"] == "pass"


def test_saturated_stars_are_skipped():
    d = diagnose({"w1mpro": 1.8, "w1mag": 7.7, "w1snr": 3.0, "nb": 1, "w1nm": 2, "w1m": 10}, {"ra": 0.0, "dec": 0.0})
    assert d["verdict"] == "saturated" and d["tests_failed"] == 0


# H-0016 section 4d: the Catalog entry J234829.46-440418.4 and the Reject Table's second extraction of the same star, as IRSA
# returned it on 2026-11-05 (one of the two of 19 marked rel = 'r', with no best_use_cntr). NAMED is the commoner case, where
# the duplicate's best_use_cntr is the bad Catalog entry: same values, with that one field filled in.
CAT = dict(BAD, designation="J234829.46-440418.4", cntr=3579044001351016240, w1mpro=12.720, w1snr=8.2)
REJ = {"designation": "J234829.25-440418.2", "cntr": "3579044001351037152", "sep_arcsec": 2.25, "w1mpro": 11.001,
       "w2mpro": 11.025, "w1snr": 47.1, "w1mag": 11.011, "w1nm": 29, "w1m": 29, "nb": 1, "use_src": 0, "rel": "r",
       "best_use_cntr": None}
NAMED = dict(REJ, best_use_cntr="3579044001351016240")


def test_best_duplicate_finds_the_clean_second_extraction():
    d = best_duplicate(CAT, [REJ])
    assert d["designation"] == "J234829.25-440418.2" and d["names_catalog_entry"] is False
    assert d["w1mpro"] == 11.001 and d["w2mpro"] == 11.025 and d["w1snr"] == 47.1 and d["sep_arcsec"] == 2.25
    assert d["w1mag"] == 11.011 and abs(d["w1_correction"] + 1.719) < 1e-9
    assert best_duplicate(CAT, [NAMED])["names_catalog_entry"] is True
    assert best_duplicate(CAT, []) is None


def test_best_duplicate_rejects_low_snr_selected_sources_and_the_rest():
    assert best_duplicate(CAT, [dict(REJ, w1snr=24.0)]) is None          # below the floor of 25
    assert best_duplicate(dict(CAT, w1snr=20.0), [REJ]) is None          # 47.1 is not three times the catalogue's 20
    assert best_duplicate(CAT, [dict(REJ, use_src=1)]) is None           # not a duplicate left out of the Catalog
    assert best_duplicate(CAT, [dict(REJ, nb=2)]) is None                # a blended fit
    assert best_duplicate(CAT, [dict(REJ, sep_arcsec=3.2)]) is None      # too far to be the same star
    assert best_duplicate(CAT, [dict(REJ, w1nm=20)]) is None             # detected in 69% of the frames
    assert best_duplicate(CAT, [dict(REJ, w1snr=None)]) is None and best_duplicate(CAT, [dict(REJ, w1m=0)]) is None


def test_best_duplicate_prefers_the_entry_that_names_the_catalogue_entry_then_the_nearest():
    near = dict(REJ, designation="near", cntr="3579044001351037153", sep_arcsec=0.6, best_use_cntr="3579044001351099999")
    nearer = dict(near, designation="nearer", sep_arcsec=0.4, best_use_cntr=None)
    d = best_duplicate(CAT, [near, nearer, NAMED])
    assert d["designation"] == "J234829.25-440418.2" and d["names_catalog_entry"] is True and d["sep_arcsec"] == 2.25
    d = best_duplicate(CAT, [near, nearer])
    assert d["designation"] == "nearer" and d["names_catalog_entry"] is False


def test_identifiers_stay_strings(monkeypatch):
    d = best_duplicate(CAT, [REJ])
    assert d["cntr"] == "3579044001351037152" and isinstance(d["cntr"], str)
    # a float would turn ...240 and ...241 into the same number; the comparison is on the digits
    assert float("3579044001351016240") == float("3579044001351016241")
    assert best_duplicate(CAT, [dict(REJ, best_use_cntr="3579044001351016241")])["names_catalog_entry"] is False
    assert best_duplicate(dict(CAT, cntr="3579044001351016240"), [NAMED])["names_catalog_entry"] is True

    # and reject_entries() reads them from IRSA's CSV as text (a null best_use_cntr would otherwise make the column float).
    # The first data row is IRSA's row for this star (2026-11-05); the second is invented, to have a best_use_cntr to read.
    class Resp:
        text = ("designation,ra,dec,cntr,coadd_id,w1mpro,w1snr,w1mag,w2mpro,w2snr,w1nm,w1m,nb,cc_flags,rel,use_src,best_use_cntr\n"
                "J234829.25-440418.2,357.1218925,-44.0717246,3579044001351037152,3579m440_ac51,11.001,47.1,11.011,11.025,52.7,"
                "29,29,1,0000,r,0,\n"
                "J234829.66-440420.0,357.1236000,-44.0722000,3579044001351037153,3579m440_ac51,15.9,3.1,,,,2,29,1,0000,,1,"
                "3579044001351016240\n")
    monkeypatch.setattr(allwise, "request", lambda *a, **k: Resp)
    rows, prov = allwise.reject_entries(357.122756, -44.071804)
    assert prov.status == "ok" and prov.rows_kept == 2 and rows[0]["sep_arcsec"] < rows[1]["sep_arcsec"]
    assert abs(rows[0]["sep_arcsec"] - 2.25) < 0.01
    assert rows[0]["cntr"] == "3579044001351037152" and rows[0]["best_use_cntr"] is None and rows[0]["rel"] == "r"
    assert rows[1]["best_use_cntr"] == "3579044001351016240" and rows[1]["w1mag"] is None and rows[1]["rel"] is None
    assert rows[0]["cc_flags"] == "0000" and rows[0]["use_src"] == 0 and rows[0]["nb"] == 1
    d = best_duplicate(CAT, rows)
    assert d["designation"] == "J234829.25-440418.2" and d["cntr"] == "3579044001351037152"


def test_reject_entries_tells_a_failed_query_from_an_empty_one(monkeypatch):
    class Resp:
        text = "designation,ra,dec,cntr,coadd_id,w1mpro,w1snr,w1mag,w2mpro,w2snr,w1nm,w1m,nb,cc_flags,rel,use_src,best_use_cntr\n"
    monkeypatch.setattr(allwise, "request", lambda *a, **k: Resp)
    rows, prov = allwise.reject_entries(10.0, -20.0)
    assert rows == [] and prov.status == "empty"

    def down(*a, **k):
        raise RuntimeError("IRSA unavailable after 2 attempts")
    monkeypatch.setattr(allwise, "request", down)
    rows, prov = allwise.reject_entries(10.0, -20.0)
    assert rows == [] and prov.status == "unavailable" and "IRSA unavailable" in prov.notes[0]

    class Html:
        text = "<html>Service temporarily unavailable</html>"
    monkeypatch.setattr(allwise, "request", lambda *a, **k: Html)
    assert allwise.reject_entries(10.0, -20.0)[1].status == "unavailable"


def _allwise_finding(store, reject):
    ctx = store.context()
    ctx["allwise"] = dict(CAT)
    ctx["gaia"].update({"ra": 10.0, "dec": -20.0, "pmra": 0.0, "pmdec": 0.0})
    if reject is not None:
        ctx["allwise_reject"] = reject
    store.write_context(ctx)
    c = [x for x in skeptic.run(store, write=False)["checks"] if x["id"] == "allwise_fit"][0]
    assert c["status"] == "fail" and "profile-fit failure" in c["finding"]  # the level does not depend on the lookup
    return c["finding"]


def test_skeptic_gives_the_reject_table_magnitude_when_there_is_a_duplicate(dusty_case):
    f = _allwise_finding(dusty_case, {"status": "ok", "entries": [REJ], "duplicate": best_duplicate(CAT, [REJ])})
    assert "J234829.25-440418.2" in f and "W1 = 11.001" in f and "W2 = 11.025" in f and "w1snr = 47.1" in f
    assert '2.25" away' in f and "-1.719 mag" in f and "w1mpro = 12.720" in f
    assert "could not be queried" not in f and "No clean second extraction" not in f
    no_w2 = dict(best_duplicate(CAT, [REJ]), w2mpro=None)
    f = _allwise_finding(dusty_case, {"status": "ok", "entries": [REJ], "duplicate": no_w2})
    assert "W1 = 11.001" in f and "W2" not in f


def test_skeptic_says_so_when_the_reject_table_could_not_be_queried(dusty_case):
    f = _allwise_finding(dusty_case, {"status": "unavailable", "entries": [], "duplicate": None})
    assert "Reject Table could not be queried" in f and "not known" in f
    assert "No clean second extraction" not in f  # a failed query is not "no duplicate"


def test_skeptic_says_none_was_found_when_the_reject_table_has_no_duplicate(dusty_case):
    for status, entries in (("empty", []), ("ok", [dict(REJ, use_src=1)])):
        f = _allwise_finding(dusty_case, {"status": status, "entries": entries, "duplicate": None})
        assert "No clean second extraction" in f and 'within 3"' in f and "could not be queried" not in f
    assert "Reject Table" not in _allwise_finding_without_lookup(dusty_case)


def _allwise_finding_without_lookup(store):
    ctx = store.context()
    ctx.pop("allwise_reject", None)
    store.write_context(ctx)
    return [x for x in skeptic.run(store, write=False)["checks"] if x["id"] == "allwise_fit"][0]["finding"]


def test_fetch_looks_up_the_reject_table_only_for_a_suspect_entry(dusty_case, monkeypatch):
    from oddsky import fetch as fetch_mod

    calls = []

    def fake_rejects(ra, dec, radius_arcsec=3.0):
        calls.append((ra, dec))
        return [dict(NAMED)], Provenance(archive="fake", rows_kept=1)

    monkeypatch.setattr(fetch_mod.allwise, "reject_entries", fake_rejects)
    monkeypatch.setattr(fetch_mod.allwise, "catalog", lambda ra, dec, r: (dict(CAT), Provenance(archive="fake", rows_kept=1)))
    rep = fetch_mod.fetch(dusty_case, ("allwise",))
    rej = dusty_case.context()["allwise_reject"]  # read back from disk: the key survives fetch()'s final save
    assert calls == [(CAT["ra"], CAT["dec"])] and rep["allwise_reject"]["status"] == "ok"
    assert rej["status"] == "ok" and rej["duplicate"]["w1mpro"] == 11.001 and rej["duplicate"]["names_catalog_entry"] is True
    assert rej["entries"][0]["best_use_cntr"] == "3579044001351016240" and rej["duplicate"]["cntr"] == "3579044001351037152"
    assert dusty_case.context()["allwise"]["cntr"] == 3579044001351016240 and "allwise_reject" in dusty_case.provenance()

    # a re-fetch whose Reject query fails keeps the earlier answer, and reports the failure
    monkeypatch.setattr(fetch_mod.allwise, "reject_entries",
                        lambda ra, dec, radius_arcsec=3.0: ([], Provenance(archive="fake", status="unavailable")))
    rep = fetch_mod.fetch(dusty_case, ("allwise",))
    assert rep["allwise_reject"]["status"] == "unavailable" and dusty_case.context()["allwise_reject"]["status"] == "ok"

    # a first lookup that fails is stored as unavailable, never as "no duplicate"
    ctx = dusty_case.context()
    del ctx["allwise_reject"]
    dusty_case.write_context(ctx)
    fetch_mod.fetch(dusty_case, ("allwise",))
    assert dusty_case.context()["allwise_reject"] == {"status": "unavailable", "entries": [], "duplicate": None}

    # a trustworthy entry is not looked up (IRSA is slow), and a stale lookup is dropped
    calls.clear()
    monkeypatch.setattr(fetch_mod.allwise, "reject_entries", fake_rejects)
    monkeypatch.setattr(fetch_mod.allwise, "catalog", lambda ra, dec, r: (dict(GOOD), Provenance(archive="fake", rows_kept=1)))
    rep = fetch_mod.fetch(dusty_case, ("allwise",))
    assert calls == [] and "allwise_reject" not in rep and "allwise_reject" not in dusty_case.context()
