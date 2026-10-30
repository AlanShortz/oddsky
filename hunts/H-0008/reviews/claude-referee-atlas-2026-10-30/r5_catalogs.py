"""r5: catalogue context (outside the Oddsky tools except gaia.adql):
 - Gaia DR3 sources within 10" (the ATLAS/WISE blend), with an estimate of each one's share of the ATLAS forced flux;
 - Gaia DR3 astrophysical_parameters, vari_* tables, and the G-flux scatter compared with stars of similar G within 3';
 - ALeRCE difference-image detections: where on the sky is the varying flux (target or neighbour)?
 - AllWISE / 2MASS photometry (IRSA TAP) for the SED."""
import io
import os
import sys
import time

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import TARGETS  # noqa: E402

from oddsky.data.gaia import adql  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
ZTF = {"J180624": "ZTF22abjkknd", "J183040": "ZTF22aalviwh"}

for k, T in TARGETS.items():
    ra, dec, sid = T["ra"], T["dec"], T["gaia"]
    print("=" * 30, k, T["name"])
    g = adql(f"""SELECT source_id, ra, dec, phot_g_mean_mag AS G, phot_bp_mean_mag AS BP, phot_rp_mean_mag AS RP, bp_rp, parallax,
      parallax_error, pmra, pmdec, ruwe, phot_variable_flag, ipd_frac_multi_peak, ipd_gof_harmonic_amplitude, phot_bp_rp_excess_factor,
      phot_g_n_obs, phot_g_mean_flux_over_error AS g_foe, phot_g_mean_flux_error*SQRT(phot_g_n_obs)/phot_g_mean_flux AS g_rel_scatter,
      teff_gspphot, logg_gspphot, mh_gspphot, distance_gspphot, ag_gspphot, ebpminrp_gspphot,
      DISTANCE(POINT(ra, dec), POINT({ra}, {dec}))*3600 AS sep
      FROM gaiadr3.gaia_source WHERE 1=CONTAINS(POINT(ra, dec), CIRCLE({ra}, {dec}, {10 / 3600}))""").sort_values("sep")
    g = g.rename(columns={"g": "G", "bp": "BP", "rp": "RP"})
    # share of the ATLAS forced-PSF flux at the target position: a neighbour at separation s adds flux * exp(-s^2 / (4 sigma^2))
    # (PSF-weighted overlap of two Gaussians) with ATLAS FWHM ~ 2.4 px * 1.86"/px = 4.5" (sigma 1.9"). o band ~ (G + RP) / 2.
    sig = 2.4 * 1.86 / 2.355
    om = np.where(g.RP.notna(), (g.G + g.RP) / 2, g.G - 0.5)
    g["o_est"] = om
    g["w_atlas"] = 10 ** (-0.4 * om) * np.exp(-g.sep**2 / (4 * sig**2))
    # WISE W1 (6.1" FWHM): use RP as a crude proxy for the relative IR flux of the red neighbours
    sw = 6.1 / 2.355
    g["w_wise"] = 10 ** (-0.4 * g.RP.fillna(g.G - 1)) * np.exp(-g.sep**2 / (4 * sw**2))
    tgt = g.source_id == sid
    print(g.drop(columns=["ra", "dec"]).round(3).to_string(index=False))
    print(f"  predicted ATLAS-o fraction of forced flux from the Gaia target: {g.w_atlas[tgt].sum() / g.w_atlas.sum():.3f} "
          f"(Gaia sources only; unresolved companions and the diffuse background not included)")
    print(f"  predicted W1 fraction from the target (RP proxy): {g.w_wise[tgt].sum() / g.w_wise.sum():.3f}")
    print(f"  Gaia G within 1.0\" of the target other than itself: {(g.sep[~tgt] < 1.0).sum()}")
    for tab in ("astrophysical_parameters", "vari_summary", "vari_classifier_result", "vari_microlensing", "vari_long_period_variable"):
        try:
            v = adql(f"SELECT * FROM gaiadr3.{tab} WHERE source_id = {sid}")
            if len(v) == 0:
                print(f"  {tab}: none")
            else:
                d = v.iloc[0].dropna().to_dict()
                keep = {kk: vv for kk, vv in d.items() if any(s in kk for s in ("teff", "logg", "mh", "distance", "ag_", "abi", "spectraltype",
                        "classprob", "flags_", "radius", "lum", "ebpminrp", "evolstage", "mass", "age", "class", "best"))} if tab == "astrophysical_parameters" else d
                print(f"  {tab}:", {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in keep.items()})
        except Exception as e:  # noqa: BLE001
            print(f"  {tab}: ERROR {e}")
    # comparison stars: G within 0.5 mag, within 3', single-looking
    tg = float(g.G[tgt].iloc[0])
    c = adql(f"""SELECT source_id, phot_g_mean_mag AS G, phot_g_n_obs, phot_g_mean_flux_error*SQRT(phot_g_n_obs)/phot_g_mean_flux AS s, ruwe, bp_rp
      FROM gaiadr3.gaia_source WHERE 1=CONTAINS(POINT(ra, dec), CIRCLE({ra}, {dec}, {180 / 3600}))
      AND phot_g_mean_mag BETWEEN {tg - 0.5} AND {tg + 0.5}""").rename(columns={"g": "G"})
    ts = float(g.g_rel_scatter[tgt].iloc[0])
    print(f"  G-flux scatter: target {ts:.4f} (n_obs {int(g.phot_g_n_obs[tgt].iloc[0])}); {len(c)} comparison stars within 3' and 0.5 mag: "
          f"median {c.s.median():.4f}, 90th pct {c.s.quantile(0.9):.4f}, target percentile {100 * (c.s < ts).mean():.0f}; "
          f"comparison with bp_rp > 2.5: median {c[c.bp_rp > 2.5].s.median():.4f} (n {int((c.bp_rp > 2.5).sum())})")
    # ALeRCE difference-image detections
    try:
        det = requests.get(f"https://api.alerce.online/ztf/v1/objects/{ZTF[k]}/detections", timeout=60).json()
        d = pd.DataFrame(det)
        print(f"  ALeRCE {ZTF[k]}: {len(d)} detections; columns with positions: {[c_ for c_ in ('ra', 'dec') if c_ in d]}")
        if len(d):
            d["pos"] = d.isdiffpos.astype(float) > 0 if "isdiffpos" in d else True
            for sgn, dd in d.groupby("pos"):
                dra = (dd.ra - ra) * np.cos(np.radians(dec)) * 3600
                dde = (dd.dec - dec) * 3600
                print(f"    isdiffpos={sgn}: n {len(dd)}, mjd {dd.mjd.min():.1f}-{dd.mjd.max():.1f}, mean offset from AllWISE position "
                      f"(E, N) = ({dra.mean():+.2f}, {dde.mean():+.2f})\" +- ({dra.std() / np.sqrt(len(dd)):.2f}, {dde.std() / np.sqrt(len(dd)):.2f}); "
                      f"magpsf range {dd.magpsf.min():.2f}-{dd.magpsf.max():.2f}, fid {sorted(dd.fid.unique())}")
                for _, s in g.head(6).iterrows():
                    ex = (s.ra - ra) * np.cos(np.radians(dec)) * 3600
                    ey = (s.dec - dec) * 3600
                    print(f"      Gaia {s.source_id} G {s.G:.2f} at (E, N) = ({ex:+.2f}, {ey:+.2f}); detections' mean distance from it "
                          f"{np.hypot(dra.mean() - ex, dde.mean() - ey):.2f}\"")
            if "distnr" in d:
                print(f"    distnr (alert to nearest PS1/ZTF ref source) median {d.distnr.median():.2f}\", sgscore etc not shown")
    except Exception as e:  # noqa: BLE001
        print("  ALeRCE: ERROR", e)
    # AllWISE + 2MASS
    q = (f"SELECT designation, w1mpro, w1sigmpro, w2mpro, w2sigmpro, w3mpro, w3snr, w4mpro, w4snr, j_m_2mass, h_m_2mass, k_m_2mass, cc_flags, ext_flg, var_flg, nb "
         f"FROM allwise_p3as_psd WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra}, {dec}, {2 / 3600}))=1")
    r = requests.post("https://irsa.ipac.caltech.edu/TAP/sync", data={"QUERY": q, "FORMAT": "csv"}, timeout=300)
    a = pd.read_csv(io.StringIO(r.text))
    print("  AllWISE+2MASS:", a.round(3).to_dict("records"))
    if len(a):
        a = a.iloc[0]
        print(f"  colours: J-K {a.j_m_2mass - a.k_m_2mass:.2f}, H-K {a.h_m_2mass - a.k_m_2mass:.2f}, K-W1 {a.k_m_2mass - a.w1mpro:.2f}, "
              f"W1-W2 {a.w1mpro - a.w2mpro:.2f}, W2-W3 {a.w2mpro - a.w3mpro:.2f} (W3 snr {a.w3snr})")
    time.sleep(1)
