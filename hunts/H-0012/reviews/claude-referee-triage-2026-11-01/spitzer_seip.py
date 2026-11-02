"""Spitzer cryogenic-era (2003-2009) IRAC/MIPS fluxes at the leads from the SEIP source list (IRSA TAP slphotdr4),
to see each source before WISE (2010). Fluxes in uJy (3.8" diameter aperture, i1..i4 = 3.6/4.5/5.8/8.0 um).

    uv run python hunts/H-0012/reviews/claude-referee-triage-2026-11-01/spitzer_seip.py
"""
import json
from pathlib import Path

import pyvo

HERE = Path(__file__).resolve().parent
L = json.loads((HERE / "leads.json").read_text())
svc = pyvo.dal.TAPService("https://irsa.ipac.caltech.edu/TAP")
out = {}
for d in L:
    q = f"""SELECT objid, ra, dec, i1_f_ap1, i1_df_ap1, i2_f_ap1, i2_df_ap1, i3_f_ap1, i4_f_ap1, m1_f_psf,
    i1_fluxtype, i2_fluxtype FROM slphotdr4 WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{d['ra']},{d['dec']},{3/3600}))=1"""
    try:
        t = svc.run_sync(q).to_table().to_pandas()
        out[d["lead"]] = dict(status="ok", rows=t.to_dict("records"))
    except Exception as e:  # noqa: BLE001
        out[d["lead"]] = dict(status=f"ERR {e}"[:200], rows=[])
    r = out[d["lead"]]["rows"]
    print(d["lead"], out[d["lead"]]["status"], [{k: (round(v, 1) if isinstance(v, float) else v) for k, v in x.items()
                                                 if k in ("i1_f_ap1", "i2_f_ap1", "i3_f_ap1", "i4_f_ap1", "m1_f_psf")} for x in r][:2], flush=True)
(HERE / "spitzer_seip.json").write_text(json.dumps(out, indent=1, default=str))
