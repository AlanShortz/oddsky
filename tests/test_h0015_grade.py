"""The H-0015 DR4 astrometric forecast grader (hunts/H-0015/predictions/dr4_astrometric_grade.py): self-test, the rules of
the forecast document, the required identity check, and the sealed sample."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "hunts/H-0015/predictions/dr4_astrometric_grade.py"


def load():
    spec = importlib.util.spec_from_file_location("h0015_grade", P)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_self_test_passes():
    assert load().self_test()


def test_significance_rule():
    g = load()
    row = lambda **k: pd.Series(dict(dchi2=30.0, err_scale=1.0, theta_e=2.0) | k)  # noqa: E731
    assert g.significant(row())
    assert not g.significant(row(dchi2=24.9))
    assert not g.significant(row(err_scale=3.1))
    assert not g.significant(row(theta_e=0.0)) and not g.significant(row(theta_e=51.0))


def test_missing_idmap_is_an_error_not_a_skip(tmp_path):
    """Referee: the identity check used to be skipped silently when the id map was missing."""
    g = load()
    sample = pd.read_csv(g.SAMPLE, dtype={"source_id": str})
    res, st, _ = g._synthetic(sample, 2, 1.5, (3.0, False, 0.1), True)
    g._write(tmp_path, res, st, None)
    with pytest.raises(g.InputError, match="idmap"):
        g.run(tmp_path)
    assert g.main(["--dir", str(tmp_path)]) == 2


def test_f3_unbounded_limit_is_unresolvable_and_heavy_detection_false():
    g = load()
    e = lambda **k: pd.DataFrame([dict(source_id="x", forecast="F3", eligible=True, why="", significant=False, dchi2=1.0,  # noqa: E731
                                       theta_e=0.1, M_best=0.5, M_lo95=0.01, M_ul95=2.0, M_gt3_sigma=0.0) | k])
    assert g.grade(e())["F3"]["outcome"] == "TRUE"
    assert g.grade(e(M_ul95=np.inf))["F3"]["outcome"] == "UNRESOLVABLE"
    assert g.grade(e(M_ul95=np.inf, significant=True, M_lo95=6.0))["F3"]["outcome"] == "FALSE"
    assert g.grade(e(M_ul95=7.0))["F3"]["outcome"] == "FALSE"


def test_sample_targets_and_controls():
    s = pd.read_csv(ROOT / "hunts/H-0015/predictions/dr4_astrometric_sample.csv", dtype={"source_id": str})
    for tag in ("F2", "F3", "F4"):
        assert s.forecast.str.contains(tag).sum() == 1
    assert s[s.forecast.str.contains("F2")].source_id.iloc[0] == "6020322385418675200"   # OS-0020
    assert s[s.forecast.str.contains("F3")].source_id.iloc[0] == "5952322268527918208"   # OS-0021
    assert s[s.forecast.str.contains("F4")].source_id.iloc[0] == "170329679884731008"    # OS-0016
    assert s.forecast.str.contains("F1").sum() >= 100
    c = s[s.forecast == "F5"]
    assert 200 <= len(c) <= 500 and not set(c.source_id) & set(s[s.forecast != "F5"].source_id)
