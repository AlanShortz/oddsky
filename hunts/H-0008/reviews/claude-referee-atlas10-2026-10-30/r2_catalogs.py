"""r2: catalogue context for the seven stars (Gaia DR3 via oddsky.data.gaia.adql; Gaia alerts index hunts/H-0005/alerts.csv).
 - Gaia DR3 sources within 10": G, colour, parallax, RUWE, ipd flags, variability flag; predicted share of the ATLAS forced flux
   (Gaussian PSF overlap, FWHM 4.5") and of the WISE flux (6.1");
 - astrophysical_parameters and vari_* tables for the target;
 - Gaia DR3 G-flux scatter (2014.6-2017.4) vs stars within 3' and 0.5 mag (sensitive to events inside the DR3 window);
 - ecliptic latitude; AllWISE/2MASS colours; Gaia alerts within 60".
"""
import os
import sys

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import GeocentricTrueEcliptic, SkyCoord

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import H8, targets  # noqa: E402

from oddsky.data.gaia import adql  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
T = targets()
ROOT = os.path.abspath(os.path.join(H8, "..", ".."))
a = pd.read_csv(os.path.join(ROOT, "hunts", "H-0005", "alerts.csv"), skipinitialspace=True)
a.columns = [c_.strip("# ") for c_ in a.columns]
ac = SkyCoord(a.RaDeg.values * u.deg, a.DecDeg.values * u.deg)
s3 = pd.read_csv(os.path.join(H8, "work", "sky3_strong.csv"), dtype={"g_source_id": str}).drop_duplicates("designation")
print(f"Gaia alerts index: {len(a)} alerts, last {a.Date.max()}")

for k, t in T.items():
    ra, dec, sid = t["ra"], t["dec"], t["gaia"]
    c = SkyCoord(ra * u.deg, dec * u.deg)
    ecl = c.transform_to(GeocentricTrueEcliptic())
    row = s3[s3.designation == t["name"]].iloc[0]
    print("=" * 40, k, t["name"], f"l={t['l']:.2f} b={t['b']:+.2f} ecliptic lat {ecl.lat.deg:+.1f}")
    print(f"  AllWISE W1 {row.w1mpro:.2f} W2 {row.w2mpro:.2f} W3 {row.w3mpro:.2f} W4 {row.w4mpro:.2f} J {row.j_m_2mass:.2f} "
          f"K {row.k_m_2mass:.2f}; W1-W2 {row.w1mpro - row.w2mpro:+.2f} W2-W3 {row.w2mpro - row.w3mpro:+.2f} J-K "
          f"{row.j_m_2mass - row.k_m_2mass:.2f}; ext_flg {row.ext_flg}; AllWISE-Gaia sep {row.g_sep:.2f}\" n_gaia_3as {row.n_gaia_3as}")
    g = adql(f"""SELECT source_id, ra, dec, phot_g_mean_mag AS G, phot_rp_mean_mag AS RP, bp_rp, parallax, parallax_error, pmra, pmdec,
      ruwe, phot_variable_flag, ipd_frac_multi_peak, ipd_gof_harmonic_amplitude, phot_bp_rp_excess_factor, phot_g_n_obs,
      phot_g_mean_flux_error*SQRT(phot_g_n_obs)/phot_g_mean_flux AS g_rel_scatter, non_single_star,
      teff_gspphot, logg_gspphot, distance_gspphot, ag_gspphot,
      DISTANCE(POINT(ra, dec), POINT({ra}, {dec}))*3600 AS sep
      FROM gaiadr3.gaia_source WHERE 1=CONTAINS(POINT(ra, dec), CIRCLE({ra}, {dec}, {10 / 3600}))""").sort_values("sep")
    g = g.rename(columns={"g": "G", "rp": "RP"})
    g["source_id"] = g.source_id.astype("int64").astype(str)
    sig = 2.4 * 1.86 / 2.355
    om = np.where(g.RP.notna(), (g.G + g.RP) / 2, g.G - 0.5)
    g["w_atlas"] = 10 ** (-0.4 * om) * np.exp(-g.sep**2 / (4 * sig**2))
    sw = 6.1 / 2.355
    g["w_wise"] = 10 ** (-0.4 * g.RP.fillna(g.G - 1)) * np.exp(-g.sep**2 / (4 * sw**2))
    tgt = g.source_id == sid
    print(g.drop(columns=["ra", "dec"]).round(3).to_string(index=False))
    if tgt.any():
        print(f"  Gaia-only predicted fraction of ATLAS forced flux from the target: {g.w_atlas[tgt].sum() / g.w_atlas.sum():.3f}; "
              f"of W1 (RP proxy): {g.w_wise[tgt].sum() / g.w_wise.sum():.3f}")
        print(f"  target sep from AllWISE position {float(g.sep[tgt].iloc[0]):.2f}\"; other Gaia sources within 2\": "
              f"{int(((g.sep < 2) & ~tgt).sum())}")
    else:
        print("  TARGET GAIA ID NOT FOUND within 10\"")
    for tab in ("astrophysical_parameters", "vari_summary", "vari_classifier_result", "vari_microlensing",
                "vari_long_period_variable", "vari_eclipsing_binary", "vari_short_timescale"):
        try:
            v = adql(f"SELECT * FROM gaiadr3.{tab} WHERE source_id = {sid}")
            if len(v) == 0:
                print(f"  {tab}: none")
            else:
                d = v.iloc[0].dropna().to_dict()
                if tab == "astrophysical_parameters":
                    d = {kk: vv for kk, vv in d.items() if any(s in kk for s in (
                        "teff", "logg", "mh_", "distance", "ag_", "spectraltype", "classprob_dsc_combmod", "lum", "evolstage",
                        "radius", "ew_espels_halpha", "classlabel_espels"))}
                print(f"  {tab}:", {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in d.items()})
        except Exception as e:  # noqa: BLE001
            print(f"  {tab}: ERROR {str(e)[:120]}")
    if tgt.any():
        tg = float(g.G[tgt].iloc[0])
        cmp_ = adql(f"""SELECT phot_g_mean_mag AS G, phot_g_n_obs,
          phot_g_mean_flux_error*SQRT(phot_g_n_obs)/phot_g_mean_flux AS s, bp_rp, ruwe
          FROM gaiadr3.gaia_source WHERE 1=CONTAINS(POINT(ra, dec), CIRCLE({ra}, {dec}, {180 / 3600}))
          AND phot_g_mean_mag BETWEEN {tg - 0.5} AND {tg + 0.5}""")
        ts = float(g.g_rel_scatter[tgt].iloc[0])
        print(f"  DR3 G-flux scatter: target {ts:.4f} (n_obs {int(g.phot_g_n_obs[tgt].iloc[0])}); {len(cmp_)} stars within 3' and "
              f"0.5 mag: median {cmp_.s.median():.4f}, 90th {cmp_.s.quantile(0.9):.4f}, 99th {cmp_.s.quantile(0.99):.4f}; "
              f"target percentile {100 * (cmp_.s < ts).mean():.1f}")
    s = ac.separation(c).arcsec
    near = np.where(s < 60)[0]
    print(f"  Gaia alerts within 60\": {len(near)}" + "".join(
        f"\n    {a.Name.iloc[j]} {s[j]:.1f}\" {a.Date.iloc[j]} G={a.AlertMag.iloc[j]} hist {a.HistoricMag.iloc[j]} "
        f"class={a.Class.iloc[j]} | {a.Comment.iloc[j]}" for j in near))
    o = np.argsort(s)[:3]
    print("  nearest alerts:", [(a.Name.iloc[j], round(s[j] / 60, 1), a.Date.iloc[j][:10]) for j in o], "(arcmin)")
