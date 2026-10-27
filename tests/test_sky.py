import numpy as np
import pandas as pd

from oddsky.sky.neowise_pixel import afterglow_flag, features, visits


def fake(rng, cntr, w1, w2, n_vis=21, spike=None, glow=None):
    rows = []
    for k in range(n_vis):
        t0 = 56700 + 182.6 * k
        a1, a2 = w1, w2
        if glow and k >= glow:                      # afterglow: W2 up 0.6, W1 up 0.3, sustained
            a1, a2 = w1 - 0.3, w2 - 0.6
        if spike is not None and k == spike:        # one-visit glitch
            a1, a2 = w1 - 0.5, w2 - 0.8
        for j in range(12):
            rows.append((cntr, t0 + j * 0.1, a1 + rng.normal(0, 0.02), 0.02, a2 + rng.normal(0, 0.03), 0.03))
    return rows


def test_afterglow_found_and_impostors_rejected(rng):
    rows = []
    rows += fake(rng, 1, 10.0, 10.05)                   # quiet star
    rows += fake(rng, 2, 10.5, 10.55, glow=8)            # afterglow from visit 8
    rows += fake(rng, 3, 11.0, 11.05, spike=10)          # single-visit spike
    rows += fake(rng, 4, 10.0, 9.4, glow=8)              # already dusty before (W1-W2 = 0.6)
    df = pd.DataFrame(rows, columns=["allwise_cntr", "mjd", "w1", "w1e", "w2", "w2e"])
    df[["w1", "w1e", "w2", "w2e"]] = df[["w1", "w1e", "w2", "w2e"]].astype("float32")
    v = visits(df)
    assert v.groupby("allwise_cntr").size().min() == 21
    f = features(v, pd.DataFrame({"allwise_cntr": [1, 2, 3, 4]}))
    flags = dict(zip(f.allwise_cntr, afterglow_flag(f), strict=True))
    assert flags == {1: False, 2: True, 3: False, 4: False}
    star = f.set_index("allwise_cntr").loc[2]
    assert 0.5 < star.w2_rise < 0.7 and 0.2 < star.dcolor_at_rise < 0.4
