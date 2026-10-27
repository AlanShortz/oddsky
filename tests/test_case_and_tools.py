import pytest

from oddsky import skeptic
from oddsky.replay import replay
from oddsky.tools import Toolbox


def test_claims_must_cite_real_calls(dusty_case):
    tb = Toolbox(author="test")
    r = tb.describe_series("OS-0001", "NEOWISE:W2")
    assert r["call_id"] == "K1"
    tb.add_claim("OS-0001", "W2 brightened by ~0.8 mag", "computed", [r["call_id"]])
    with pytest.raises(ValueError):
        tb.add_claim("OS-0001", "made up", "computed", ["K99"])
    c = dusty_case.load()
    assert c.claims[0].tag == "computed" and c.claims[0].calls == ["K1"]


def test_hypothesis_requires_known_class_and_claims(dusty_case):
    tb = Toolbox(author="test")
    tb.add_claim("OS-0001", "a dip", "observed")
    tb.add_hypothesis("OS-0001", "dust_occultation", "a clump", supports=["C1"], confidence=0.6)
    with pytest.raises(ValueError):
        tb.add_hypothesis("OS-0001", "aliens", "nope")
    with pytest.raises(ValueError):
        tb.add_hypothesis("OS-0001", "pulsation", "x", supports=["C9"])


def test_prediction_is_graded_by_the_data(dusty_case):
    tb = Toolbox(author="test")
    tb.register_prediction("OS-0001", "dip in the second half", 0.8, "AAVSO:V", 59520, 59540, ">", 0.3,
                           statistic="median", baseline_start=59000, baseline_end=59400)
    tb.register_prediction("OS-0001", "brighter than 11", 0.1, "AAVSO:V", 59800, 59900, "<", 11.0)
    assert tb.check_prediction("OS-0001", "P1")["outcome"] == "true"
    assert tb.check_prediction("OS-0001", "P2")["outcome"] == "false"


def test_blind_mode_hides_open_tools(dusty_case):
    tb = Toolbox(mode="blind", blind_root=dusty_case.path)
    with pytest.raises(PermissionError):
        tb.literature("OS-0001")
    with pytest.raises(PermissionError):
        tb.check_prediction("OS-0001", "P1")
    assert tb.case_overview(".")["target"] == "hidden (blind trial)"


def test_skeptic_flags_the_bright_red_neighbour(dusty_case):
    rep = skeptic.run(dusty_case)
    blend = next(c for c in rep["checks"] if c["id"] == "blend_neowise")
    assert blend["status"] == "warn"
    conf = next(c for c in rep["checks"] if c["id"] == "confirmation")
    assert conf["status"] == "pass"  # two observers


def test_replay_reproduces_the_ledger(dusty_case):
    tb = Toolbox(author="test")
    tb.describe_series("OS-0001", "AAVSO:V")
    tb.find_excursions("OS-0001", "AAVSO:V")
    tb.wise_color("OS-0001")
    res = replay("OS-0001")
    assert len(res) == 3 and all(r["match"] for r in res)


def test_retracted_claims_stay_in_the_record(dusty_case):
    tb = Toolbox(author="test")
    tb.add_claim("OS-0001", "x", "speculated")
    tb.retract_claim("OS-0001", "C1", "probe, not a claim")
    c = dusty_case.load()
    assert c.claims[0].retracted == "probe, not a claim" and len(c.claims) == 1


def test_digest10_ignores_last_bit_platform_noise():
    from oddsky.case.store import digest, digest10

    a = {"x": 0.1 + 0.2, "y": [1.0, 2.0000000000000004], "n": 3}
    b = {"x": 0.30000000000000004 * (1 + 2e-16), "y": [1.0, 2.0], "n": 3}
    assert digest(a) != digest(b)
    assert digest10(a) == digest10(b)
    assert digest10({"x": 0.3}) != digest10({"x": 0.3001})
