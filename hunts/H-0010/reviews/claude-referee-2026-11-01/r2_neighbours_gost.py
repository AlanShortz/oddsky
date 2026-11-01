"""r2: (a) every Gaia DR3 source within 6" of the 21 candidates from the ESA Gaia TAP, with the blend diagnostics
(RUWE, ipd_frac_multi_peak, ipd_gof_harmonic_amplitude, BP/RP excess and C* (Riello+2021), blended/contaminated BP/RP
transit counts, duplicated_source); (b) GOST scan geometry (scan angle, FoV) for each candidate over the DR3 span, matched
to the epoch-photometry transits in r3. Writes data/neighbours_tap.csv and data/gost_<sid>.csv.
Run: uv run python -I hunts/H-0010/reviews/claude-referee-2026-11-01/r2_neighbours_gost.py"""
import os, re, sys, time
import numpy as np, pandas as pd, requests
import pyvo

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")
C = pd.read_csv(os.path.join(D, "candidates21.csv"), dtype={"source_id": str})


def cstar(c, bprp):
    """Riello et al. 2021 corrected excess factor C* and its 1-sigma scatter for the source's G."""
    x = bprp
    corr = np.where(x < 0.5, 1.154360 + 0.033772 * x + 0.032277 * x**2,
           np.where(x < 4.0, 1.162004 + 0.011464 * x + 0.049255 * x**2 - 0.005879 * x**3, 1.057572 + 0.140537 * x))
    return c - corr


def sig_cstar(g):
    return 0.0059898 + 8.817481e-12 * g**7.618399


out = os.path.join(D, "neighbours_tap.csv")
if not os.path.exists(out):
    tap = pyvo.dal.TAPService("https://gea.esac.esa.int/tap-server/tap")
    rows = []
    for c in C.itertuples():
        q = f"""SELECT '{c.source_id}' AS target, s.source_id, s.ra, s.dec,
          DISTANCE(POINT(s.ra,s.dec), POINT({c.ra},{c.dec}))*3600 AS sep,
          s.phot_g_mean_mag, s.phot_bp_mean_mag, s.phot_rp_mean_mag, s.bp_rp, s.ruwe, s.ipd_frac_multi_peak,
          s.ipd_gof_harmonic_amplitude, s.ipd_frac_odd_win, s.phot_bp_rp_excess_factor, s.phot_bp_n_blended_transits,
          s.phot_rp_n_blended_transits, s.phot_bp_n_contaminated_transits, s.phot_rp_n_contaminated_transits,
          s.phot_bp_n_obs, s.phot_rp_n_obs, s.phot_g_n_obs, s.duplicated_source, s.astrometric_params_solved,
          s.parallax, s.parallax_error, s.pmra, s.pmdec, s.phot_variable_flag, s.visibility_periods_used,
          s.astrometric_excess_noise, s.astrometric_excess_noise_sig, s.scan_direction_strength_k1, s.scan_direction_strength_k2,
          s.scan_direction_strength_k3, s.scan_direction_strength_k4, s.teff_gspphot, s.ag_gspphot
          FROM gaiadr3.gaia_source AS s
          WHERE 1=CONTAINS(POINT(s.ra,s.dec), CIRCLE({c.ra},{c.dec},{6/3600}))"""
        for attempt in range(3):
            try:
                t0 = time.time()
                r = tap.run_sync(q, timeout=180).to_table().to_pandas()
                print(c.name, len(r), f"{time.time()-t0:.1f}s", flush=True)
                rows.append(r)
                break
            except Exception as e:  # noqa: BLE001
                print(c.name, "TAP error", str(e)[:120], flush=True)
                time.sleep(5)
    N = pd.concat(rows, ignore_index=True)
    N["cstar"] = cstar(N.phot_bp_rp_excess_factor, N.bp_rp)
    N["cstar_sig"] = N.cstar / sig_cstar(N.phot_g_mean_mag)
    N.to_csv(out, index=False)
N = pd.read_csv(out, dtype={"target": str, "source_id": str})
pd.set_option("display.width", 250)
for c in C.itertuples():
    n = N[N.target == c.source_id].sort_values("sep")
    me = n[n.source_id == c.source_id].iloc[0]
    others = n[n.source_id != c.source_id]
    print(f"\n{c.name} G {me.phot_g_mean_mag:.2f} BP-RP {me.bp_rp:.2f} RUWE {me.ruwe:.2f} ipd_mp {me.ipd_frac_multi_peak} "
          f"ipd_gof_h {me.ipd_gof_harmonic_amplitude:.3f} oddwin {me.ipd_frac_odd_win} C* {me.cstar:.3f} ({me.cstar_sig:.1f} sig) "
          f"BP blended/contam {me.phot_bp_n_blended_transits}/{me.phot_bp_n_contaminated_transits} of {me.phot_bp_n_obs}, "
          f"RP {me.phot_rp_n_blended_transits}/{me.phot_rp_n_contaminated_transits} of {me.phot_rp_n_obs}; dup {me.duplicated_source}; "
          f"{me.astrometric_params_solved}p; aen_sig {me.astrometric_excess_noise_sig:.1f}")
    for o in others.itertuples():
        print(f"    nb {o.source_id} {o.sep:.2f}\" G {o.phot_g_mean_mag:.2f} (dG {o.phot_g_mean_mag - me.phot_g_mean_mag:+.2f}) "
              f"BP-RP {o.bp_rp if o.bp_rp == o.bp_rp else float('nan'):.2f} RUWE {o.ruwe if o.ruwe == o.ruwe else float('nan'):.2f} "
              f"var {o.phot_variable_flag}")

# GOST
s = requests.Session()
s.get("https://gaia.esac.esa.int/gost/index.jsp", timeout=60)
pat = re.compile(r"<kind>(\w+)</kind><ccdRow>(\d)</ccdRow><ccdStripNo>(\d+)</ccdStripNo>.*?<fov>(\w+)</fov>.*?<scanAngle>([-\d.Ee]+)</scanAngle>"
                 r".*?<eventTcbBarycentricJulianDateAtBarycentre>([\d.]+)</eventTcbBarycentricJulianDateAtBarycentre>", re.S)
for c in C.itertuples():
    p = os.path.join(D, f"gost_{c.source_id}.csv")
    if os.path.exists(p):
        continue
    for attempt in range(3):
        try:
            r = s.get("https://gaia.esac.esa.int/gost/GostServlet", params={"ra": c.ra, "dec": c.dec, "service": 1, "srcname": c.name,
                      "inputmode": "single", "from": "2014-07-25T00:00:00", "to": "2017-05-29T00:00:00"}, timeout=400)
            ev = pat.findall(r.text)
            break
        except Exception as e:  # noqa: BLE001
            print("GOST error", c.name, e); ev = []; time.sleep(10)
    g = pd.DataFrame(ev, columns=["kind", "row", "strip", "fov", "scan_angle", "bjd"])
    g = g[g.kind == "AF"].astype({"row": int, "strip": int, "scan_angle": float, "bjd": float})
    g["t_gaia"] = g.bjd - 2455197.5  # epoch photometry time scale
    g = g.groupby((g.t_gaia.diff().fillna(1) > 0.01).cumsum()).agg(t_gaia=("t_gaia", "min"), fov=("fov", "first"),
                                                                       row=("row", "first"), scan_angle=("scan_angle", "mean"))
    g.to_csv(p, index=False)
    print("GOST", c.name, len(g), "transits", flush=True)
