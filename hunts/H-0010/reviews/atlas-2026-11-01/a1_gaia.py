"""a1: Gaia inputs. (a) Gaia DR3 epoch photometry for the 8 targets through oddsky.data.gaia_epoch.fetch_report(ids,
releases=("Gaia DR3",)) -> data/epoch_<sid>.csv (t_mjd, mag, err, band, flag); (b) every Gaia DR3 source within 10" of each target
from the ESA Gaia TAP (one cone per target) -> data/neighbours10.csv; (c) for each target the share of the ATLAS c and o forced
flux that belongs to the target, for a 2015-17 PSF (maj 3.8 px) and a narrow one (2.6 px), using lib.psf_weight.
Run: uv run python -I hunts/H-0010/reviews/atlas-2026-11-01/a1_gaia.py"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, KEYS, gaia_to_atlas_ujy, psf_weight, targets  # noqa: E402

from oddsky.data.gaia_epoch import fetch_report  # noqa: E402

T = targets()
ids = [T[k]["sid"] for k in KEYS]
need = [s for s in ids if not os.path.exists(os.path.join(DATA, f"epoch_{s}.csv"))]
if need:
    got, rep = fetch_report(need, releases=("Gaia DR3",))
    print("fetch_report:", json.dumps(rep["releases"]))
    for sid, df in got.items():
        df.to_csv(os.path.join(DATA, f"epoch_{sid}.csv"), index=False)
for k in KEYS:
    p = os.path.join(DATA, f"epoch_{T[k]['sid']}.csv")
    if os.path.exists(p):
        d = pd.read_csv(p)
        print(f"{k}: epoch rows {len(d)}; G {int((d.band == 'G').sum())}, BP {int((d.band == 'BP').sum())}, RP {int((d.band == 'RP').sum())}; "
              f"flagged {int(d.flag.notna().sum())}")
    else:
        print(f"{k}: NO epoch photometry returned")

out = os.path.join(DATA, "neighbours10.csv")
if not os.path.exists(out):
    import pyvo
    tap = pyvo.dal.TAPService("https://gea.esac.esa.int/tap-server/tap")
    rows = []
    for k in KEYS:
        t = T[k]
        q = f"""SELECT '{t['sid']}' AS target, s.source_id, s.ra, s.dec,
          DISTANCE(POINT(s.ra,s.dec), POINT({t['ra']},{t['dec']}))*3600 AS sep,
          s.phot_g_mean_mag, s.phot_bp_mean_mag, s.phot_rp_mean_mag, s.bp_rp, s.ruwe, s.phot_variable_flag
          FROM gaiadr3.gaia_source AS s
          WHERE 1=CONTAINS(POINT(s.ra,s.dec), CIRCLE({t['ra']},{t['dec']},{10/3600}))"""
        for attempt in range(3):
            try:
                t0 = time.time()
                r = tap.run_sync(q, timeout=180).to_table().to_pandas()
                r["source_id"] = r.source_id.astype(str)
                print(k, len(r), f"{time.time() - t0:.1f}s", flush=True)
                rows.append(r)
                break
            except Exception as e:  # noqa: BLE001
                print(k, "TAP error", str(e)[:120], flush=True)
                time.sleep(10)
    pd.concat(rows, ignore_index=True).to_csv(out, index=False)
N = pd.read_csv(out, dtype={"target": str, "source_id": str})

shares = {}
pd.set_option("display.width", 250)
for k in KEYS:
    t = T[k]
    n = N[N.target == t["sid"]].sort_values("sep").copy()
    fc, fo = zip(*[gaia_to_atlas_ujy(r.phot_g_mean_mag, r.phot_bp_mean_mag, r.phot_rp_mean_mag) for r in n.itertuples()])
    n["fc"], n["fo"] = fc, fo
    me = n[n.source_id == t["sid"]].iloc[0]
    sh = {}
    for maj in (3.8, 3.2, 2.6):
        w = psf_weight(n.sep.values, maj)
        w8 = np.where(n.sep.values <= 8.0, w, 0.0)
        sh[maj] = dict(c=float(me.fc / np.sum(w8 * n.fc)), o=float(me.fo / np.sum(w8 * n.fo)),
                       c10=float(me.fc / np.sum(w * n.fc)), o10=float(me.fo / np.sum(w * n.fo)))
    shares[k] = dict(fc_star=float(me.fc), fo_star=float(me.fo), share=sh,
                     n8=int(((n.sep > 0.01) & (n.sep <= 8)).sum()))
    print(f"\n{k} {t['name']}  G {t['G']:.2f} BP {t['BP']:.2f} RP {t['RP']:.2f}  -> c {me.fc:.0f} uJy, o {me.fo:.0f} uJy (Gaia-predicted)")
    print("  neighbours within 10\":")
    print(n[["source_id", "sep", "phot_g_mean_mag", "bp_rp", "ruwe", "phot_variable_flag", "fc", "fo"]].round(2).to_string(index=False))
    for maj, v in sh.items():
        print(f"  target share of the ATLAS forced flux (PSF maj {maj} px; sources <= 8\"): c {v['c']:.2f}, o {v['o']:.2f}  "
              f"(<= 10\": c {v['c10']:.2f}, o {v['o10']:.2f})")
json.dump(shares, open(os.path.join(DATA, "a1_shares.json"), "w"), indent=1)
