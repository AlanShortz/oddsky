"""H-0015 s2: Gaia DR3 inputs for every target, fetched before the archive closes (2026-11-25 12:00 CET until DR4).

Small async TAP jobs through the polite H-0014 client (`oddsky.dr4day.archive.Archive`, 2 s between requests, backoff on
429/5xx). Every failure is written to data/gaia_dr3_errors.jsonl with its message; a failed query never becomes an empty
result.

  1. gaiadr3.gaia_source for the target ids: astrometry (parallax, proper motion and their errors, RUWE, excess noise,
     number of good AL observations, matched transits, visibility periods), photometry, IPD blend indicators, GSP-Phot.
  2. Every Gaia DR3 source within 3" of each target (blending inside and next to Gaia's window).
  3. A 3" cone at OGLE-2011-BLG-0462 (17:51:40.19 -29:53:26.3, J2000), the one confirmed isolated stellar-mass black hole.

Outputs: data/gaia_dr3.csv, data/gaia_dr3_neighbours.csv, data/ob110462_dr3.csv.
Run: uv run python -I hunts/H-0015/scripts/s2_gaia_dr3.py
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from oddsky.dr4day.archive import Archive
from oddsky.dr4day.config import release

ROOT = Path(__file__).resolve().parents[3]
D = ROOT / "hunts/H-0015/data"

COLS = ("source_id, ra, dec, ra_error, dec_error, ref_epoch, parallax, parallax_error, pmra, pmra_error, pmdec, pmdec_error, "
        "parallax_pmra_corr, parallax_pmdec_corr, pmra_pmdec_corr, astrometric_params_solved, astrometric_n_obs_al, "
        "astrometric_n_good_obs_al, astrometric_n_bad_obs_al, astrometric_matched_transits, visibility_periods_used, "
        "astrometric_excess_noise, astrometric_excess_noise_sig, ruwe, astrometric_gof_al, astrometric_chi2_al, "
        "nu_eff_used_in_astrometry, pseudocolour, ipd_frac_multi_peak, ipd_frac_odd_win, ipd_gof_harmonic_amplitude, "
        "duplicated_source, phot_g_mean_mag, phot_g_mean_flux_over_error, phot_bp_mean_mag, phot_rp_mean_mag, bp_rp, "
        "phot_bp_rp_excess_factor, phot_variable_flag, non_single_star, l, b, teff_gspphot, logg_gspphot, "
        "distance_gspphot, ag_gspphot, has_epoch_photometry")


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    t = pd.read_csv(D / "targets_input.csv", dtype={"source_id": str})
    ids = sorted(set(t.source_id.dropna()))
    arc = Archive(release("dr3"))
    errors = []

    def run(tag, fn):
        try:
            df = fn()
            print(f"{tag}: {len(df)} rows")
            return df
        except Exception as e:  # noqa: BLE001  recorded as an error, never as an empty table
            errors.append({"query": tag, "error": f"{type(e).__name__}: {e}"[:500]})
            print(f"{tag}: ERROR {e}")
            return None

    src = run("gaia_source", lambda: arc.tap_in(f"SELECT {COLS} FROM gaiadr3.gaia_source WHERE source_id IN ({{ids}})",
                                                ids, per=200))
    if src is not None:
        missing = sorted(set(ids) - set(src.source_id.astype(str)))
        for m in missing:
            errors.append({"query": "gaia_source", "error": f"id {m} not returned"})
        src.to_csv(D / "gaia_dr3.csv", index=False)

    # one indexed cone per target with literal coordinates: a self-join on gaia_source hits the 60 s anonymous limit
    def cones():
        parts = []
        for r in src.itertuples():
            q = ("SELECT source_id, ra, dec, phot_g_mean_mag, bp_rp, parallax, pmra, pmdec, astrometric_params_solved, ruwe, "
                 f"DISTANCE(POINT(ra, dec), POINT({r.ra!r}, {r.dec!r})) * 3600 AS sep_arcsec FROM gaiadr3.gaia_source "
                 f"WHERE 1 = CONTAINS(POINT(ra, dec), CIRCLE({r.ra!r}, {r.dec!r}, 3.0 / 3600)) AND source_id <> {r.source_id}")
            try:
                d = arc.tap(q, sync=True)
                d.insert(0, "target_id", str(r.source_id))
                parts.append(d)
            except Exception as e:  # noqa: BLE001
                errors.append({"query": f"neighbours {r.source_id}", "error": f"{type(e).__name__}: {e}"[:500]})
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

    nb = run("neighbours", cones) if src is not None else None
    if nb is not None:
        nb.to_csv(D / "gaia_dr3_neighbours.csv", index=False)

    ob = run("ob110462", lambda: arc.tap(
        f"SELECT {COLS}, DISTANCE(POINT(ra, dec), POINT(267.917458, -29.890639)) * 3600 AS sep_arcsec "
        "FROM gaiadr3.gaia_source WHERE 1 = CONTAINS(POINT(ra, dec), CIRCLE(267.917458, -29.890639, 3.0 / 3600))"))
    if ob is not None:
        ob.to_csv(D / "ob110462_dr3.csv", index=False)

    errors += arc.errors
    with open(D / "gaia_dr3_errors.jsonl", "w") as f:
        for e in errors:
            f.write(json.dumps(e, default=str) + "\n")
    print(f"{len(errors)} errors -> data/gaia_dr3_errors.jsonl")


if __name__ == "__main__":
    main()
