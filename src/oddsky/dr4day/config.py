"""One switch for the Gaia DR4-day pipeline: which release the pipeline talks to.

`release("dr3")` is the stand-in used for dry runs before DR4 exists; `release("dr4")` is what runs on release day
(2026-12-02, ~11:00 UTC). Everything that differs between releases lives here: the DataLink label, the TAP schema,
table and column names, the epoch-photometry span, and the paging limits. Nothing else in `oddsky.dr4day` names a
release.

If DR4 turns out to name something differently, fix it without touching code: pass `--set key=value` to
`scripts/dr4_day.py` (e.g. `--set tables.vari_microlensing=gaiadr4.vari_microlensing_v2`), or set the environment
variable ODDSKY_GAIA_RELEASE to choose the preset. The probe stage (`probe.py`) reports what the archive actually serves,
so the overrides can be read off its output.

DR4 facts (checked 2026-11-02; sources in hunts/H-0014/README.md): 66 months, 2014-07-25 10:30 to 2020-01-20 22:00 UTC;
epoch photometry for all ~2.8 billion sources, by DataLink only (not TAP); TAP schema `gaiadr4`; `gaia_source` keeps only the
~2.0 billion sources with good astrometry and photometry, the rest are in `all_source_*` (has_epoch_photometry is in
`all_source_flags`); `vari_microlensing` has 1,360 rows. Anonymous DataLink requests take at most 50 source ids; a logged-in
session takes 5,000.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path

TAP = "https://gea.esac.esa.int/tap-server/tap"
DATALINK = "https://gea.esac.esa.int/data-server/data"
LINKS = "https://gea.esac.esa.int/data-server/datalink/links"
LOGIN = "https://gea.esac.esa.int/tap-server/login"



@dataclass(frozen=True)
class Release:
    key: str                      # "dr3" | "dr4"
    name: str                     # DataLink RELEASE label
    schema: str                   # TAP schema
    epoch_start_mjd: float        # first and last epoch-photometry times of the release
    epoch_end_mjd: float
    previous: str                 # the release our source ids come from (all Oddsky ids are Gaia DR3 ids)
    # logical table -> fully qualified TAP table
    tables: dict = field(default_factory=dict)
    # DR3 -> this release's ids: (table, old id column, new id column, distance column [mas], magnitude-difference column)
    neighbourhood: tuple = ()
    flags_table: str = ""         # where has_epoch_photometry lives
    microlensing_class: str = "MICROLENSING"
    classifier_cols: tuple = ("best_class_name", "best_class_score")   # (best class, its score) in vari_classifier_result
    tap: str = TAP
    datalink: str = DATALINK
    links: str = LINKS
    retrieval_epoch: str = "EPOCH_PHOTOMETRY"
    data_structure: str = "DATAMODEL_STANDARD"
    chunk: int = 50               # ids per DataLink request (50 anonymous; 5,000 with a logged-in session)
    chunk_logged_in: int = 5000
    pause_s: float = 2.0          # between archive requests: the archive is shared, and DR4 day will be its busiest
    stand_in: bool = False        # a dry run: never writes into sealed prediction directories

    def table(self, logical: str) -> str:
        return self.tables[logical]

    @property
    def tag(self) -> str:
        return self.key

    def in_span(self, t_mjd: float, margin: float = 0.0) -> bool:
        return self.epoch_start_mjd - margin <= t_mjd <= self.epoch_end_mjd + margin


def _tables(schema: str) -> dict:
    return {t: f"{schema}.{t}" for t in ("gaia_source", "vari_summary", "vari_classifier_result", "vari_microlensing",
                                          "vari_long_period_variable", "vari_eclipsing_binary")}


PRESETS: dict[str, Release] = {
    # The stand-in: Gaia DR3 (2014-07-25 to 2017-05-28; epoch photometry for ~11.8 million variable sources only).
    # Its neighbourhood table maps DR2 -> DR3 ids; the dry run asks it for our DR3 ids as if they were the old ids, which
    # exercises the code path (most DR3 ids equal their DR2 ids).
    "dr3": Release(key="dr3", name="Gaia DR3", schema="gaiadr3", epoch_start_mjd=56863.0, epoch_end_mjd=57901.0,
                   previous="Gaia DR2", tables=_tables("gaiadr3"),
                   neighbourhood=("gaiadr3.dr2_neighbourhood", "dr2_source_id", "dr3_source_id", "angular_distance",
                                  "magnitude_difference"),
                   flags_table="gaiadr3.gaia_source", stand_in=True),
    # Gaia DR4 (2014-07-25 10:30 to 2020-01-20 22:00 UTC). Table and column names from the draft data model of
    # 2026-06-26 (dr3_neighbourhood: DR4 id in `source_id`; the classifier columns renamed; the microlensing class label is
    # not given in the draft, "MICROLENSING" is assumed). Check everything with the probe stage on the day.
    "dr4": Release(key="dr4", name="Gaia DR4", schema="gaiadr4", epoch_start_mjd=56863.44, epoch_end_mjd=58868.92,
                   previous="Gaia DR3", tables=_tables("gaiadr4"),
                   neighbourhood=("gaiadr4.dr3_neighbourhood", "dr3_source_id", "source_id", "angular_distance",
                                  "magnitude_difference"),
                   flags_table="gaiadr4.all_source_flags",
                   classifier_cols=("classifier_best_class_name", "classifier_best_class_prob")),
}

DR4_SPAN_END_MJD = PRESETS["dr4"].epoch_end_mjd


def release(key: str | None = None, overrides: dict[str, str] | None = None) -> Release:
    """The preset for `key` ("dr3" or "dr4"; default from ODDSKY_GAIA_RELEASE, else "dr3"), with `overrides` applied.
    Override keys are field names (`name=Gaia DR4`, `chunk=50`, `pause_s=3`) or `tables.<logical>=<table>`."""
    key = (key or os.environ.get("ODDSKY_GAIA_RELEASE") or "dr3").lower().replace("gaia", "").replace(" ", "")
    if key not in PRESETS:
        raise ValueError(f"unknown release {key!r}; choose one of {sorted(PRESETS)}")
    r = PRESETS[key]
    for k, v in (overrides or {}).items():
        if k.startswith("tables."):
            r = replace(r, tables={**r.tables, k.split(".", 1)[1]: v})
        elif k in ("neighbourhood", "classifier_cols"):
            r = replace(r, **{k: tuple(x.strip() for x in v.split(","))})
        elif hasattr(r, k):
            cur = getattr(r, k)
            val = (v.lower() in ("1", "true", "yes")) if isinstance(cur, bool) else type(cur)(v) if cur is not None else v
            r = replace(r, **{k: val})
        else:
            raise ValueError(f"unknown release setting {k!r}")
    return r


def parse_overrides(items: list[str] | None) -> dict[str, str]:
    out = {}
    for it in items or []:
        k, sep, v = it.partition("=")
        if not sep:
            raise ValueError(f"--set needs key=value, got {it!r}")
        out[k.strip()] = v.strip()
    return out


def run_root() -> Path:
    """Big data lives outside the repo: ~/oddsky-runs/h0014 (override with ODDSKY_H0014_RUNS)."""
    return Path(os.environ.get("ODDSKY_H0014_RUNS", Path.home() / "oddsky-runs" / "h0014"))


def run_dir(rel: Release) -> Path:
    d = run_root() / rel.key
    d.mkdir(parents=True, exist_ok=True)
    return d
