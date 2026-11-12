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


def test_hunt_field_round_trips_and_exports(dusty_case):
    from oddsky.export import export_web

    c = dusty_case.load()
    c.hunt = "H-0004"
    dusty_case.save(c)
    assert dusty_case.load().hunt == "H-0004"
    out = dusty_case.path.parent.parent / "web" / "data"
    ids = export_web(out)
    assert "OS-0001" in ids
    import json

    index = json.loads((out / "index.json").read_text())
    assert next(i for i in index["cases"] if i["id"] == "OS-0001")["hunt"] == "H-0004"


def test_referee_reports_are_exported(dusty_case):
    import json

    from oddsky.export import export_web

    (dusty_case.path / "reviews").mkdir()
    (dusty_case.path / "reviews" / "claude-referee-2026-10-27.md").write_text("# Referee\n\n## Verdict\n\nSurvives.\n")
    out = dusty_case.path.parent.parent / "web" / "data"
    export_web(out)
    payload = json.loads((out / "cases" / "OS-0001.json").read_text())
    assert payload["reviews"][0]["file"] == "claude-referee-2026-10-27.md"
    assert "Survives." in payload["reviews"][0]["markdown"]


def test_fetch_does_not_overwrite_claims_recorded_during_a_long_fetch(dusty_case, monkeypatch):
    """fetch() reloads the case before saving: a claim added while an archive was queued must survive."""
    from oddsky import fetch as fetch_mod
    from oddsky.case.model import Claim

    store = dusty_case

    def slow_lightcurve(ra, dec):
        c = store.load()
        c.claims.append(Claim(id="C1", text="recorded mid-fetch", tag="observed", calls=[]))
        store.save(c)
        import pandas as pd

        from oddsky.data.provenance import Provenance
        return pd.DataFrame(), Provenance(archive="fake", status="empty")

    monkeypatch.setattr(fetch_mod.neowise, "lightcurve", slow_lightcurve)
    fetch_mod.fetch(store, ("neowise",))
    assert [c.id for c in store.load().claims] == ["C1"]


def test_listed_case_figures_are_exported(dusty_case):
    import json

    import pytest

    from oddsky.export import export_web

    figs = dusty_case.path / "figures"
    figs.mkdir(exist_ok=True)
    (figs / "shown.png").write_bytes(b"png")
    (figs / "working.png").write_bytes(b"png")
    (figs / "index.yaml").write_text("- file: shown.png\n  caption: What it shows.\n")
    out = dusty_case.path.parent.parent / "web" / "data"
    export_web(out)
    payload = json.loads((out / "cases" / "OS-0001.json").read_text())
    assert payload["figures"] == [{"file": "shown.png", "caption": "What it shows.", "alt": ""}]
    assert (out / "figures" / "OS-0001" / "shown.png").read_bytes() == b"png"
    assert not (out / "figures" / "OS-0001" / "working.png").exists()
    (figs / "index.yaml").write_text("- file: gone.png\n")
    with pytest.raises(FileNotFoundError):
        export_web(out)
