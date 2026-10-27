import numpy as np

from oddsky.data import atlas

SAMPLE = """###MJD          m      dm   uJy   duJy F err chi/N     RA        Dec        x        y     maj  min   phi  apfit mag5sig Sky   Obs
57300.60000  16.500  0.010   912    8.4 o   0  1.20  80.07901  36.60953  1000.0  1000.0  2.1  2.0  10.0 -0.30  19.40 20.1 01a57300o0123c
57300.62000  16.510  0.011   903    9.0 o   0  1.10  80.07901  36.60953  1000.0  1000.0  2.1  2.0  10.0 -0.30  19.40 20.1 01a57300o0130c
57301.60000  21.000  1.000    12     40 c   0  0.90  80.07901  36.60953  1000.0  1000.0  2.1  2.0  10.0 -0.30  19.00 20.1 02a57301c0010c
57302.60000 -17.000  0.500  -300     60 o   0  0.95  80.07901  36.60953  1000.0  1000.0  2.1  2.0  10.0 -0.30  19.40 20.1 02a57302o0010c
57303.60000  16.400  0.010   990    8.0 o   1  1.00  80.07901  36.60953  1000.0  1000.0  2.1  2.0  10.0 -0.30  19.40 20.1 03a57303o0010c
"""


def test_flux_to_mag_zero_point_and_errors():
    mag, err, flag = atlas.flux_to_mag([3631e6, 1000.0], [10.0, 100.0])
    assert abs(mag[0]) < 1e-3
    assert abs(mag[1] - 16.4) < 1e-6
    assert abs(err[1] - 0.10857) < 1e-4
    assert list(flag) == ["", ""]


def test_low_snr_and_negative_flux_become_limits():
    mag, err, flag = atlas.flux_to_mag([12.0, -300.0, 0.0], [40.0, 60.0, 0.0])
    assert list(flag) == ["upper_limit", "upper_limit", "atlas_bad"]
    assert abs(mag[0] - (23.9 - 2.5 * np.log10(200.0))) < 1e-6  # 5 sigma limit
    assert np.isnan(err[0]) and np.isfinite(mag[1])


def test_parse_and_series():
    raw = atlas.parse(SAMPLE)
    assert len(raw) == 5 and list(raw.F) == ["o", "o", "c", "o", "o"]
    df = atlas.to_series(raw)
    assert set(df.band) == {"ATLAS_o", "ATLAS_c"}
    assert df.flag.tolist() == ["", "", "upper_limit", "upper_limit", "atlas_bad"]
    assert df.camera.tolist() == ["01a", "01a", "02a", "02a", "03a"]


def test_nightly_bins_combine_in_flux_space():
    df = atlas.to_series(atlas.parse(SAMPLE))
    n = atlas.nightly_bins(df)
    first = n[(n.band == "ATLAS_o") & (n.flag == "")].iloc[0]
    assert first.n_exp == 2
    assert 16.49 < first.mag < 16.52
    assert first.err < 0.011  # better than either single exposure
    # the negative-flux night stays a limit, the bad point is gone
    assert "atlas_bad" not in set(n.flag)
    assert (n.flag == "upper_limit").sum() == 2


def test_lightcurve_without_credentials_is_unavailable(monkeypatch, tmp_path):
    for k in ("ATLAS_TOKEN", "ATLAS_USER", "ATLAS_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("ODDSKY_CACHE", str(tmp_path))
    df, prov = atlas.lightcurve(10.0, 20.0)
    assert df.empty and prov.status == "unavailable"


def test_lightcurve_from_raw_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("ODDSKY_CACHE", str(tmp_path))
    f = tmp_path / "raw.txt"
    f.write_text(SAMPLE)
    df, prov = atlas.lightcurve(80.079, 36.6095, raw_cache=str(f))
    assert prov.status == "ok" and prov.rows_raw == 5 and prov.rows_kept == 2
    assert any("01a" in n for n in prov.notes)
