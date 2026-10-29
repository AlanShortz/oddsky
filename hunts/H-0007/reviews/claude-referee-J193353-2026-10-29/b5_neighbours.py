"""b5: AllWISE sources within 60" and Gaia DR3 sources within 30" of J193353 (raw IRSA Gator and Gaia TAP; outside the Oddsky tools)."""
import io

import numpy as np
import pandas as pd
from astropy.io import ascii as aascii

from oddsky.data.http import request

pd.set_option("display.width", 250)
RA, DEC = 293.471115, -21.3037472
p = dict(catalog="allwise_p3as_psd", spatial="cone", radius=60, radunits="arcsec", objstr=f"{RA} {DEC}", outfmt=1,
         selcols="designation,ra,dec,w1mpro,w2mpro,w3mpro,w4mpro,w1sigmpro,w2sigmpro,cc_flags,ext_flg,ph_qual,nb,j_m_2mass,h_m_2mass,k_m_2mass,w1rchi2")
a = aascii.read(request("GET", "https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query", params=p, timeout=300).text.splitlines(), format="ipac").to_pandas()
a["sep"] = 3600 * np.hypot((a.ra - RA) * np.cos(np.radians(DEC)), a.dec - DEC)
a["w1w2"] = a.w1mpro - a.w2mpro
print(a.sort_values("sep").round(3).to_string())
q = f"""SELECT source_id, ra, dec, phot_g_mean_mag, bp_rp, parallax, parallax_error, pmra, pmdec, ruwe, ipd_frac_multi_peak, ipd_gof_harmonic_amplitude,
 phot_variable_flag, non_single_star, phot_bp_rp_excess_factor, phot_g_n_obs, phot_g_mean_flux_over_error, teff_gspphot, logg_gspphot, mh_gspphot,
 distance_gspphot, ag_gspphot, classprob_dsc_combmod_star, radial_velocity, radial_velocity_error,
 DISTANCE(POINT(ra, dec), POINT({RA}, {DEC}))*3600 AS sep
 FROM gaiadr3.gaia_source WHERE CONTAINS(POINT(ra, dec), CIRCLE({RA}, {DEC}, {30/3600})) = 1 ORDER BY sep"""
r = request("POST", "https://gea.esac.esa.int/tap-server/tap/sync", data=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=q), timeout=300)
g = pd.read_csv(io.StringIO(r.text))
print(g.round(3).T.to_string())
q2 = f"""SELECT a.source_id, a.radius_flame, a.lum_flame, a.mass_flame, a.age_flame, a.evolstage_flame, a.teff_gspspec, a.logg_gspspec,
 a.ew_espels_halpha, a.classlabel_espels, a.distance_msc, a.radius_gspphot
 FROM gaiadr3.astrophysical_parameters a WHERE a.source_id = 6772245406602788608"""
r = request("POST", "https://gea.esac.esa.int/tap-server/tap/sync", data=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=q2), timeout=300)
print(pd.read_csv(io.StringIO(r.text)).T.to_string())
