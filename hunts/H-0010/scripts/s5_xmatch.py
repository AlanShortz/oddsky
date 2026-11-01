"""s5: is it known? For each of the 67:
  * hunts/H-0008/ext/reference_lenses.csv (KMTNet, OGLE EWS, OGLE GVS, Gaia DR3 microlensing, Gaia alerts, ZTF lists):
    within 6" and |t0_ref - t_event| < max(2 tE_ref, 60 d), where t_event is the Gaia peak transit or, failing that, the
    static-lens t0; also any reference event within 6" at any time;
  * the Gaia Science Alerts index (hunts/H-0005/alerts.csv): within 6", any date;
  * VSX (VizieR B/vsx/vsx on the vizier.idia.ac.za mirror): within 10";
  * SIMBAD (CfA mirror TAP): within 5", main id, object type, spectral type, number of references; and the H-0008/H-0009
    OGLE/KMT tables are covered by the reference list.
Run from the repo root: uv run python -I hunts/H-0010/scripts/s5_xmatch.py
Writes hunts/H-0010/data/xmatch.csv."""
import io
import os
import sys
import time

import numpy as np
import pandas as pd
import requests
from astropy.time import Time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, targets  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
VIZ = "https://vizier.idia.ac.za/viz-bin/asu-tsv"
SIMBAD_TAP = "https://simbad.cfa.harvard.edu/simbad/sim-tap/sync"


def dstr(m):
    return Time(m, format="mjd").iso[:10] if np.isfinite(m) else "?"


def sep(ra1, dec1, ra2, dec2):
    ra1, dec1, ra2, dec2 = map(np.radians, (ra1, dec1, ra2, dec2))
    s = np.sin((dec2 - dec1) / 2) ** 2 + np.cos(dec1) * np.cos(dec2) * np.sin((ra2 - ra1) / 2) ** 2
    return np.degrees(2 * np.arcsin(np.sqrt(s))) * 3600


def vizier(cat, ra, dec, r_arcsec, out="**"):
    for k in range(4):
        try:
            q = requests.get(VIZ, params={"-source": cat, "-c": f"{ra} {dec}", "-c.rs": r_arcsec, "-out": out,
                                          "-out.max": 50, "-out.add": "_r"}, timeout=120)
            q.raise_for_status()
            lines = [ln for ln in q.text.splitlines() if ln and not ln.startswith("#")]
            if len(lines) < 3:
                return pd.DataFrame(), "ok"
            df = pd.read_csv(io.StringIO("\n".join([lines[0]] + lines[3:])), sep="\t")
            return df, "ok"
        except Exception as e:  # noqa: BLE001
            err = f"ERR {type(e).__name__}"
            time.sleep(10)
    return pd.DataFrame(), err


def simbad(ra, dec, r_arcsec):
    q = (f"SELECT b.main_id, b.otype, b.sp_type, b.nbref, DISTANCE(POINT('ICRS', b.ra, b.dec), POINT('ICRS', {ra}, {dec})) * 3600 AS sep "
         f"FROM basic AS b WHERE CONTAINS(POINT('ICRS', b.ra, b.dec), CIRCLE('ICRS', {ra}, {dec}, {r_arcsec / 3600})) = 1 "
         f"ORDER BY sep")
    for k in range(3):
        try:
            r = requests.post(SIMBAD_TAP, data=dict(request="doQuery", lang="adql", format="csv", query=q), timeout=120)
            r.raise_for_status()
            return pd.read_csv(io.StringIO(r.text)), "ok"
        except Exception as e:  # noqa: BLE001
            err = f"ERR {type(e).__name__} {str(e)[:80]}"
            time.sleep(10)
    return pd.DataFrame(), err


def main():
    T = targets()
    lc = pd.read_csv(os.path.join(DATA, "lc_metrics.csv"), dtype={"source_id": str})
    T = T.merge(lc[["source_id", "t_peak", "static_t0"]], on="source_id", how="left")
    ref = pd.read_csv(os.path.join(REPO, "hunts/H-0008/ext/reference_lenses.csv"))
    al = pd.read_csv(os.path.join(REPO, "hunts/H-0005/alerts.csv"), skipinitialspace=True)
    al.columns = [c.strip().lstrip("#") for c in al.columns]
    al["mjd"] = Time(pd.to_datetime(al.Date).dt.strftime("%Y-%m-%dT%H:%M:%S").tolist(), format="isot").mjd
    rows = []
    for r in T.itertuples():
        te = r.t_peak if np.isfinite(r.t_peak) else r.static_t0
        s = sep(r.ra, r.dec, ref.ra.values, ref.dec.values)
        near = ref[s < 6].assign(sep=s[s < 6])
        win = np.maximum(2 * near.tE.fillna(30), 60)
        intime = near[np.abs(near.t0_mjd - te) < win]
        sa = sep(r.ra, r.dec, al.RaDeg.values, al.DecDeg.values)
        an = al[sa < 6].assign(sep=sa[sa < 6])
        vsx, vst = vizier("B/vsx/vsx", r.ra, r.dec, 10, out="Name,Type,max,min,Period,_r")
        sim, sst = simbad(r.ra, r.dec, 5)
        rec = dict(source_id=r.source_id,
                   ref_intime=";".join(f"{x.name}({x.source},t0 {dstr(x.t0_mjd)},tE {x.tE},{x.sep:.1f}\")"
                                       for x in intime.itertuples()),
                   ref_anytime=";".join(f"{x.name}({x.source},t0 {dstr(x.t0_mjd)},{x.sep:.1f}\")"
                                        for x in near.itertuples()),
                   gaia_alert=";".join(f"{x.Name}({x.Date[:10]},{x.Class},{x.sep:.1f}\",{str(x.Comment)[:80]})" for x in an.itertuples()),
                   vsx_status=vst,
                   vsx=";".join(f"{x['Name']}|{x['Type']}|P={x['Period']}|{float(x['_r']):.1f}\"" for x in vsx.to_dict("records")) if len(vsx) else "",
                   simbad_status=sst,
                   simbad=";".join(f"{x.main_id}|{x.otype}|{x.sp_type if isinstance(x.sp_type, str) else ''}|refs {x.nbref}|{x.sep:.1f}\""
                                   for x in sim.itertuples()) if len(sim) else "")
        rows.append(rec)
        print(r.source_id, "| ref:", rec["ref_intime"] or "-", "| any:", rec["ref_anytime"][:120] or "-", "| alert:",
              rec["gaia_alert"] or "-", "| vsx:", vst, rec["vsx"][:150] or "-", "| simbad:", sst, rec["simbad"][:200] or "-", flush=True)
        time.sleep(1)
    pd.DataFrame(rows).to_csv(os.path.join(DATA, "xmatch.csv"), index=False)


if __name__ == "__main__":
    main()
