"""H-0016: the Skeptic's AllWISE profile-fit check (offline; the catalogue row is given, not fetched)."""
import numpy as np

from oddsky import skeptic
from oddsky.data.allwise import diagnose, expected_w1snr

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
