"""Fetch field catalogues for OS-0013 SPHEREx check: AllWISE (with 2MASS), CatWISE2020, Gaia DR3 within 360"."""
import sys, urllib.parse, urllib.request
out = sys.argv[1]
RA, DEC, R = 220.96627, -76.19612, 360/3600.

def tap(url, q, fn):
    data = urllib.parse.urlencode({"QUERY": q, "FORMAT": "csv", "LANG": "ADQL", "REQUEST": "doQuery"}).encode()
    with urllib.request.urlopen(url, data=data, timeout=600) as r:
        open(f"{out}/{fn}", "wb").write(r.read())
    print(fn, "ok")

circ = f"CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{RA},{DEC},{R}))=1"
tap("https://irsa.ipac.caltech.edu/TAP/sync",
    f"SELECT designation,ra,dec,w1mpro,w1sigmpro,w2mpro,w2sigmpro,w3mpro,ph_qual,cc_flags,ext_flg,nb,na,j_m_2mass,h_m_2mass,k_m_2mass,cntr FROM allwise_p3as_psd WHERE {circ}",
    "allwise.csv")
tap("https://irsa.ipac.caltech.edu/TAP/sync",
    f"SELECT source_name,ra,dec,w1mpro,w1sigmpro,w2mpro,w2sigmpro FROM catwise_2020 WHERE {circ}",
    "catwise.csv")
tap("https://gea.esac.esa.int/tap-server/tap/sync",
    f"SELECT source_id,ra,dec,pmra,pmdec,ref_epoch,phot_g_mean_mag,phot_bp_mean_mag,phot_rp_mean_mag,parallax,ruwe FROM gaiadr3.gaia_source WHERE {circ}",
    "gaia.csv")
