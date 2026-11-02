"""Who the DR4-day pipeline looks at: every target list Oddsky already has, merged into one table.

One row per (source_id, set). `source_id` is a Gaia DR3 id as a string (19-digit ids lose precision as floats).

tier 1 (first hour; ~250 sources):
  sealed        targets of cases with ungraded predictions on a GAIA series
  cases         every Oddsky case with a Gaia DR3 id (DR4 gives each a 2014-2020 light curve)
  strong        the 118 strong NEOWISE events of H-0008/H-0009 (hunts/H-0009/work/gaia_dr3_sweep.csv), matched Gaia star
  strong_alt    the neighbour a centroid test pointed at (ensemble sample alt_source_id, never counted in the ensemble)
  h0010         the 67 Gaia classifier MICROLENSING sources missing from DR3 vari_microlensing (H-0010)
  nogaia        strong events with no Gaia DR3 star within 4": no id; a cone search in the new release may find a new source
tier 2 (hours 1-4; ~3,300 sources):
  unclassified  NEOWISE brightenings no catalogue explains (H-0008 sky3 + H-0009 sky4 `class == unclassified`)
  rcb           H-0004's WISE-selected R CrB candidates (Tisserand+2020), exact ids recovered in hunts/H-0014/data/h0004_ids.csv
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..case.store import CaseStore

COLS = ["source_id", "set", "tier", "name", "ra", "dec", "t_event", "note"]
H0014 = Path("hunts/H-0014")


def _sid(x) -> str:
    s = str(x).strip()
    return s if s.isdigit() and len(s) >= 6 else ""


def _frame(rows) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=COLS)
    df["source_id"] = df.source_id.astype(str)
    return df


def from_cases(root: Path = Path(".")) -> pd.DataFrame:
    rows = []
    for d in sorted((root / "cases").glob("OS-*")):
        try:
            c = CaseStore(d).load()
        except Exception:  # noqa: BLE001  a malformed case must not stop release day
            continue
        if not (c.target and c.target.gaia_source_id):
            continue
        sid = _sid(c.target.gaia_source_id)
        gaia_preds = [p for p in c.predictions if p.check and p.check.series.upper().startswith("GAIA") and p.resolution is None]
        common = dict(source_id=sid, name=f"{c.id} {c.target.name}", ra=c.target.ra, dec=c.target.dec, t_event=np.nan)
        rows.append(dict(common, set="cases", tier=1, note=c.title[:80]))
        if gaia_preds:
            rows.append(dict(common, set="sealed", tier=1, note=",".join(p.id for p in gaia_preds)))
    return _frame(rows)


def _positions(root: Path) -> pd.DataFrame:
    parts = []
    for f in ("hunts/H-0009/work/sky4_strong.csv", "hunts/H-0008/work/sky3_strong.csv"):
        p = root / f
        if p.exists():
            parts.append(pd.read_csv(p, dtype=str, usecols=["designation", "ra", "dec"]))
    pos = pd.concat(parts).drop_duplicates("designation") if parts else pd.DataFrame(columns=["designation", "ra", "dec"])
    return pos.set_index("designation")


def from_strong(root: Path = Path(".")) -> pd.DataFrame:
    sw = pd.read_csv(root / "hunts/H-0009/work/gaia_dr3_sweep.csv", dtype=str)
    pos = _positions(root)
    rows = []
    for r in sw.itertuples():
        ra, dec = (float(pos.loc[r.designation, "ra"]), float(pos.loc[r.designation, "dec"])) if r.designation in pos.index \
            else (np.nan, np.nan)
        sid = _sid(r.gaia_source_id) or _sid(r.survey_source_id)
        common = dict(name=r.designation, ra=ra, dec=dec, t_event=float(r.t))
        if sid:
            rows.append(dict(common, source_id=sid, set="strong", tier=1,
                             note=f"in_dr4_span={r.in_dr4_span}; off_target={r.off_target}; {r.verdict}"[:160]))
        else:
            rows.append(dict(common, source_id="", set="nogaia", tier=1, note=r.verdict[:120]))
    ens = root / "hunts/H-0009/predictions/dr4_ensemble_sample.csv"
    if ens.exists():
        e = pd.read_csv(ens, dtype=str)
        for r in e[e.alt_source_id.notna()].itertuples():
            rows.append(dict(source_id=_sid(r.alt_source_id), set="strong_alt", tier=1, name=r.designation, ra=float(r.ra),
                             dec=float(r.dec), t_event=float(r.t_event_mjd), note="centroid neighbour (ensemble alt; not counted)"))
    return _frame(rows)


def from_h0010(root: Path = Path(".")) -> pd.DataFrame:
    u = pd.read_csv(root / "hunts/H-0010/work/gaia_ml_unpub.csv", dtype=str)
    # No t_event: H-0010's times are Gaia's own peaks, and testing Gaia at Gaia's peak would be circular. Only an
    # independent instrument's time (NEOWISE) counts as an event time.
    rows = [dict(source_id=_sid(r.source_id), set="h0010", tier=1, name=r.name, ra=float(r.ra), dec=float(r.dec),
                 t_event=np.nan, note=f"{r.verdict}; P={r.p_lens}; DR3 Gaia peak MJD {r.t_peak}") for r in u.itertuples()]
    return _frame(rows)


def from_unclassified(root: Path = Path(".")) -> pd.DataFrame:
    rows = []
    for f in ("hunts/H-0009/work/sky4_classified.csv", "hunts/H-0008/work/sky3_classified.csv"):
        p = root / f
        if not p.exists():
            continue
        c = pd.read_csv(p, dtype=str)
        c = c[(c["class"] == "unclassified") & c.g_source_id.notna()]
        for r in c.itertuples():
            rows.append(dict(source_id=_sid(r.g_source_id), set="unclassified", tier=2, name=r.designation, ra=float(r.ra),
                             dec=float(r.dec), t_event=float(r.t), note=f"dW1={float(r.dw1):+.2f} dW2={float(r.dw2):+.2f}"))
    df = _frame(rows)
    return df[df.source_id != ""].drop_duplicates(["source_id", "t_event"])


def from_rcb(root: Path = Path(".")) -> pd.DataFrame:
    p = root / H0014 / "data" / "h0004_ids.csv"
    if not p.exists():
        return _frame([])
    m = pd.read_csv(p, dtype=str)
    m = m[m.source_id.notna() & (m.source_id != "")]
    rows = [dict(source_id=r.source_id, set="rcb", tier=2, name=r.id, ra=float(r.ra), dec=float(r.dec), t_event=np.nan,
                 note=f"H-0004 pool {r.pool}") for r in m.itertuples()]
    return _frame(rows)


def build(root: Path = Path("."), tiers: tuple[int, ...] = (1, 2)) -> pd.DataFrame:
    parts = [from_cases(root), from_strong(root), from_h0010(root)]
    if 2 in tiers:
        parts += [from_unclassified(root), from_rcb(root)]
    df = pd.concat([p for p in parts if len(p)], ignore_index=True)
    df = df[df.tier.isin(tiers)]
    bad = df[(df.set != "nogaia") & (df.source_id == "")]
    if len(bad):
        raise ValueError(f"{len(bad)} targets without a valid Gaia id: {bad.name.tolist()[:5]}")
    return df.reset_index(drop=True)


def unique_ids(df: pd.DataFrame) -> list[str]:
    return sorted({s for s in df.source_id if s})
