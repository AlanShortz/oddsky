"""Shared helpers for H-0015 scripts: the scanning law (GOST) per target, paths, and the per-target AL error scale."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
HUNT = ROOT / "hunts/H-0015"
DATA = HUNT / "data"
FIG = HUNT / "figures"
RUNS = Path.home() / "oddsky-runs/h0015"
GOST_RAW = RUNS / "gost"
GOST_PACKED = DATA / "gost_transits.csv.gz"

DR4_START, DR4_END = 56863.44, 58868.92
DR3_END = 57901.0
DEAD_TIME_KEEP = 0.8      # GOST ignores dead time and data loss: ~80% of forecast transits reach the ground (GOST page)


def pack_gost() -> pd.DataFrame:
    """All raw GOST exports -> one compact committed table (source_id, t_mjd (barycentric TCB), theta, plx_al, fov, row)."""
    parts = []
    for p in sorted(GOST_RAW.glob("gost_*.csv")):
        g = pd.read_csv(p, skipinitialspace=True)
        g.columns = [c.strip() for c in g.columns]
        if g.empty:
            continue
        parts.append(pd.DataFrame(dict(
            source_id=p.stem.removeprefix("gost_"),
            t_mjd=g["ObservationTimeAtBarycentre[BarycentricJulianDateInTCB]"].astype(float) - 2400000.5,
            theta=g["scanAngle[rad]"].astype(float), plx_al=g["parallaxFactorAlongScan"].astype(float),
            fov=g["Fov[FovP=preceding/FovF=following]"].astype(str).str.strip(), row=g["CcdRow[1-7]"].astype(int))))
    d = pd.concat(parts, ignore_index=True)
    d = d[(d.t_mjd >= DR4_START) & (d.t_mjd <= DR4_END)]
    d.to_csv(GOST_PACKED, index=False, float_format="%.7f")
    return d


_CACHE: dict = {}


def gost_table() -> pd.DataFrame:
    if "g" not in _CACHE:
        _CACHE["g"] = pd.read_csv(GOST_PACKED, dtype={"source_id": str})
    return _CACHE["g"]


def transits(source_id: str, end: float = DR4_END, keep: float | None = None, rng=None):
    """(t, theta, plx_al) of the forecast transits of one target up to `end`; `keep` < 1 drops transits at random."""
    g = gost_table()
    g = g[(g.source_id == str(source_id)) & (g.t_mjd <= end)]
    t, th, px = g.t_mjd.to_numpy(), g.theta.to_numpy(), g.plx_al.to_numpy()
    if keep is not None and keep < 1:
        rng = np.random.default_rng() if rng is None else rng
        m = rng.uniform(size=len(t)) < keep
        t, th, px = t[m], th[m], px[m]
    return t, th, px


def load_targets() -> pd.DataFrame:
    """targets_input.csv joined with the Gaia DR3 inputs (data/gaia_dr3.csv) and neighbour summaries."""
    t = pd.read_csv(DATA / "targets_input.csv", dtype={"source_id": str})
    g = pd.read_csv(DATA / "gaia_dr3.csv", dtype={"source_id": str})
    t = t.merge(g, on="source_id", how="left")
    nbp = DATA / "gaia_dr3_neighbours.csv"
    if nbp.exists():
        nb = pd.read_csv(nbp, dtype={"target_id": str, "source_id": str})
        gt = dict(zip(t.source_id, t.phot_g_mean_mag, strict=False))
        nb["dG"] = nb.phot_g_mean_mag - nb.target_id.map(gt)
        nb["flux_ratio"] = 10 ** (-0.4 * nb.dG)
        for r_as, tag in ((1.0, "1"), (2.0, "2")):
            s = nb[nb.sep_arcsec <= r_as].groupby("target_id").flux_ratio.sum()
            t[f"nb_flux_{tag}as"] = t.source_id.map(s).fillna(0.0)
            n = nb[nb.sep_arcsec <= r_as].groupby("target_id").size()
            t[f"nb_n_{tag}as"] = t.source_id.map(n).fillna(0).astype(int)
    return t
