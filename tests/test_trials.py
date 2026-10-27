import yaml

from oddsky.case.store import CaseStore
from oddsky.tools import Toolbox
from oddsky.trials.build import build
from oddsky.trials.score import score
from oddsky.trials.seal import verify


def test_blind_hindsight_trial_end_to_end(dusty_case, tmp_path):
    trial = tmp_path / "trials" / "t"
    trial.mkdir(parents=True)
    (trial / "spec.yaml").write_text(yaml.safe_dump({"name": "t", "packets": [
        {"id": "H01", "case": "OS-0001", "truth": "dust_occultation", "cutoff_mjd": 59450}]}))
    out = build(trial / "spec.yaml")
    packet = trial / "packets" / "H01"
    ctx = CaseStore(packet).context()
    assert "source_id" not in str(ctx) and CaseStore(packet).load().target is None
    v = CaseStore(packet).series("aavso")
    t0 = yaml.safe_load((trial / "sealed" / "answers.yaml").read_text())["packets"]["H01"]["t0_mjd"]
    assert out["answers_sha256"] and v.t_mjd.min() >= 0 and v.t_mjd.max() + t0 < 59450
    assert set(v.observer) <= {"O1", "O2"}

    # an investigator works on a copy of the packet
    import shutil
    run = trial / "runs" / "bot" / "H01"
    shutil.copytree(packet, run)
    tb = Toolbox(mode="blind", blind_root=run, author="bot")
    tb.add_hypothesis(".", "dust_occultation", "dust", confidence=0.7)
    tb.add_hypothesis(".", "pulsation", "pulses", confidence=0.3)
    tb.register_prediction(".", "the dip deepens", 0.9, "AAVSO:V", 59520 - t0, 59540 - t0, ">", 12.3)

    (trial / "revealed").mkdir()
    shutil.copy(trial / "sealed" / "answers.yaml", trial / "revealed" / "answers.yaml")
    assert verify(trial)
    card = score(trial, "bot")
    assert card["summary"]["top1"] == 1.0
    assert card["predictions"][0]["outcome"] == "true"
    assert card["summary"]["brier"] < 0.2


def test_salted_packet_plants_dips_on_momentum_dumps(dusty_case, tmp_path):
    import numpy as np
    import pandas as pd

    from oddsky.trials.build import build_packet

    t = np.arange(60000, 60027, 2 / 1440)
    dumps = [60003.0, 60006.1, 60009.2, 60012.3, 60015.4]
    dusty_case.write_series("tess", pd.DataFrame(dict(t_mjd=t, mag=0.0, err=0.001, band="TESS", survey="TESS",
                                                      flag="", camera="S40")))
    ctx = dusty_case.context()
    ctx["tess"] = {"sectors": {"40": {"desat_mjd": dumps}}}
    dusty_case.write_context(ctx)
    info = build_packet(dusty_case, tmp_path / "pk", "T99", None, {"kind": "tess_dump_dips", "depth": 0.01})
    assert len(info["planted_mjd"]) == 4 and set(info["planted_mjd"]) <= set(dumps)
    tess = CaseStore(tmp_path / "pk").series("tess")
    assert tess.mag.max() > 0.009
    assert "desat_mjd" in str(CaseStore(tmp_path / "pk").context())
