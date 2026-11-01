"""H-0011 pilot, step 3: Gaia DR3 for every sample star with a Gaia DR3 id (from SIMBAD).

gaia_source (mean G/BP/RP, n_obs, flux-over-error, RUWE, IPD multi-peak, has_epoch_photometry, variable flag),
vari_summary (std/range of G per FoV), vari_long_period_variable (period, amplitude), and the DR3 epoch photometry
(datalink via oddsky.data.gaia_epoch.fetch_report, releases=("Gaia DR3",)).

usage: 03_gaia.py mc|gal|cal
Writes work/gaia_<s>.csv, work/gaia_epoch_<s>.parquet.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from oddsky.data import gaia, gaia_epoch  # noqa: E402

WORK = Path(__file__).resolve().parents[1] / "work"


def by_ids(ids, select, table, chunk=300):
    out = []
    for i in range(0, len(ids), chunk):
        lst = ",".join(str(int(x)) for x in ids[i:i + chunk])
        out.append(gaia.adql(f"SELECT {select} FROM {table} WHERE source_id IN ({lst})", timeout=300))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def main(which: str):
    s = pd.read_csv(WORK / f"sample_{which}.csv", dtype={"gaia_dr3": "Int64"})
    ids = s.gaia_dr3.dropna().astype("int64").unique().tolist()
    cached = WORK / f"gaia_{which}.csv"
    if cached.exists():  # resume: the TAP tables are done, only the epoch photometry is missing
        src = pd.read_csv(cached)
        got, report = gaia_epoch.fetch_report(
            src.loc[src.has_epoch_photometry.astype(str).str.lower().eq("true"), "source_id"].astype("int64").tolist(),
            releases=("Gaia DR3",))
        print(report["releases"])
        pd.concat([df.assign(source_id=sid) for sid, df in got.items()], ignore_index=True).to_parquet(
            WORK / f"gaia_epoch_{which}.parquet")
        print("epoch photometry for", len(got), "stars")
        return
    src = by_ids(ids, "source_id, ra, dec, phot_g_mean_mag, phot_bp_mean_mag, phot_rp_mean_mag, phot_g_n_obs, "
                      "phot_g_mean_flux_over_error, ruwe, ipd_frac_multi_peak, phot_bp_rp_excess_factor, "
                      "has_epoch_photometry, phot_variable_flag, parallax, parallax_over_error", "gaiadr3.gaia_source")
    vs = by_ids(ids, "source_id, num_selected_g_fov, std_dev_mag_g_fov, range_mag_g_fov, in_vari_long_period_variable",
                "gaiadr3.vari_summary")
    lpv = by_ids(ids, "source_id, frequency, amplitude, median_delta_wl_rp", "gaiadr3.vari_long_period_variable")
    g = src.merge(vs, on="source_id", how="left").merge(lpv, on="source_id", how="left")
    g.to_csv(WORK / f"gaia_{which}.csv", index=False)
    print("gaia_source", len(src), "vari_summary", len(vs), "lpv", len(lpv),
          "has_epoch", int(src.has_epoch_photometry.astype(str).str.lower().eq("true").sum()), flush=True)
    ep_ids = src.loc[src.has_epoch_photometry.astype(str).str.lower().eq("true"), "source_id"].astype("int64").tolist()
    got, report = gaia_epoch.fetch_report(ep_ids, releases=("Gaia DR3",))
    print(report["releases"])
    parts = [df.assign(source_id=sid) for sid, df in got.items()]
    if parts:
        pd.concat(parts, ignore_index=True).to_parquet(WORK / f"gaia_epoch_{which}.parquet")
    print("epoch photometry for", len(got), "stars")


if __name__ == "__main__":
    main(sys.argv[1])
