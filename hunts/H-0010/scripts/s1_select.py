"""s1: re-derive the list of Gaia DR3 sources the variability classifier calls MICROLENSING but that are not in the DR3
microlensing catalogue, and collect what Gaia DR3 knows about each: gaia_source astrometry/photometry, astrophysical
parameters, vari_summary flags, and all classifier rows. Neighbours within 6" are s1b_neighbours.py.

Run from the repo root: uv run python -I hunts/H-0010/scripts/s1_select.py
Writes hunts/H-0010/data/{classifier_ml.csv, unpub.csv, gaia_source.csv, ap.csv, varisum.csv, classifier_rows.csv, vari_microlensing_classes.csv}.
source_id is a string everywhere (19-digit ids lose precision as float64)."""
import io
import os
import time

import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
TAP = "https://gea.esac.esa.int/tap-server/tap/sync"


def adql(q: str, tries: int = 3) -> pd.DataFrame:
    for k in range(tries):
        try:
            r = requests.post(TAP, data=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=q), timeout=180)
            r.raise_for_status()
            return pd.read_csv(io.StringIO(r.text), dtype={"source_id": str, "ml": str, "nb_source_id": str, "target": str})
        except Exception as e:  # noqa: BLE001
            print("TAP retry", k, type(e).__name__, str(e)[:200])
            time.sleep(10)
    raise RuntimeError("TAP failed: " + q[:200])


def inlist(ids):
    return "(" + ",".join(ids) + ")"


def main():
    allml = adql("SELECT c.source_id, c.best_class_score, m.source_id AS ml FROM gaiadr3.vari_classifier_result c "
                 "LEFT JOIN gaiadr3.vari_microlensing m ON m.source_id = c.source_id "
                 "WHERE c.best_class_name = 'MICROLENSING'")
    allml["in_vari_microlensing"] = allml.ml.notna()
    allml.drop(columns="ml").to_csv(os.path.join(DATA, "classifier_ml.csv"), index=False)
    n_cat = int(allml.in_vari_microlensing.sum())
    unpub = allml[~allml.in_vari_microlensing].copy()
    print(f"classifier MICROLENSING: {len(allml)}; in vari_microlensing: {n_cat}; not: {len(unpub)}")
    ids = unpub.source_id.tolist()
    assert all(len(s) >= 15 and s.isdigit() for s in ids)

    # how big is the catalogue, and how many of its sources are classified MICROLENSING by the classifier?
    cat = adql("SELECT m.source_id, c.best_class_name FROM gaiadr3.vari_microlensing m "
               "LEFT JOIN gaiadr3.vari_classifier_result c ON c.source_id = m.source_id")
    cat.to_csv(os.path.join(DATA, "vari_microlensing_classes.csv"), index=False)
    print(f"vari_microlensing: {len(cat)} sources; classifier best class among them:\n{cat.best_class_name.value_counts(dropna=False)}")

    gs = adql("SELECT source_id, ra, dec, l, b, parallax, parallax_error, pmra, pmdec, ruwe, phot_g_mean_mag, phot_bp_mean_mag, "
              "phot_rp_mean_mag, bp_rp, phot_bp_rp_excess_factor, ipd_frac_multi_peak, ipd_gof_harmonic_amplitude, "
              "phot_variable_flag, has_epoch_photometry, non_single_star, radial_velocity, classprob_dsc_combmod_star, "
              "classprob_dsc_combmod_quasar, classprob_dsc_combmod_galaxy, teff_gspphot, logg_gspphot, ag_gspphot, "
              "distance_gspphot FROM gaiadr3.gaia_source WHERE source_id IN " + inlist(ids))
    gs.to_csv(os.path.join(DATA, "gaia_source.csv"), index=False)
    ap = adql("SELECT source_id, teff_gspphot, logg_gspphot, mh_gspphot, distance_gspphot, azero_gspphot, teff_esphs, "
              "spectraltype_esphs, classlabel_espels, classlabel_espels_flag, evolstage_flame, radius_gspphot, lum_flame "
              "FROM gaiadr3.astrophysical_parameters WHERE source_id IN " + inlist(ids))
    ap.to_csv(os.path.join(DATA, "ap.csv"), index=False)
    vs = adql("SELECT * FROM gaiadr3.vari_summary WHERE source_id IN " + inlist(ids))
    vs.to_csv(os.path.join(DATA, "varisum.csv"), index=False)
    cl = adql("SELECT * FROM gaiadr3.vari_classifier_result WHERE source_id IN " + inlist(ids))
    cl.to_csv(os.path.join(DATA, "classifier_rows.csv"), index=False)
    print("classifier_name values:", cl.classifier_name.unique() if "classifier_name" in cl else "?")

    unpub = unpub.merge(gs, on="source_id", how="left")
    unpub.drop(columns="ml").to_csv(os.path.join(DATA, "unpub.csv"), index=False)

    # compare with the list handed over
    given = pd.read_csv("/tmp/gaia_ml_unpub.csv", dtype={"source_id": str}) if os.path.exists("/tmp/gaia_ml_unpub.csv") else None
    if given is not None:
        a, b = set(given.source_id), set(unpub.source_id)
        print(f"given list {len(a)}; re-derived {len(b)}; in both {len(a & b)}; only given {sorted(a - b)}; only mine {sorted(b - a)}")

    # neighbours within 6": s1b_neighbours.py (VizieR mirror; the ESA TAP cones took > 1 min each and stalled)


if __name__ == "__main__":
    main()
