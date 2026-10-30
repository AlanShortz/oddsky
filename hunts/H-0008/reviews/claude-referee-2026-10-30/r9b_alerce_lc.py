"""r9b: ALeRCE detections (alert stream) and forced photometry for ZTF22abjkknd (J180624) and ZTF21abahtfi (J173342)."""
import os, sys, json
import pandas as pd, requests
HERE = os.path.dirname(os.path.abspath(__file__))
pd.set_option("display.width", 250)
for oid in sys.argv[1:] or ["ZTF22abjkknd", "ZTF21abahtfi"]:
    for kind in ("detections", "forced_photometry"):
        r = requests.get(f"https://api.alerce.online/ztf/v1/objects/{oid}/{kind}", timeout=120)
        d = pd.DataFrame(r.json())
        d.to_csv(f"{HERE}/data/alerce_{oid}_{kind}.csv", index=False)
        cols = [c for c in ("mjd", "fid", "magpsf", "sigmapsf", "isdiffpos", "magpsf_corr", "sigmapsf_corr", "mag_corr", "e_mag_corr", "corrected", "dubious", "field", "rb", "drb", "procstatus", "distnr", "magnr") if c in d]
        print(oid, kind, len(d))
        if len(d):
            print(d.sort_values("mjd")[cols].round(3).to_string(max_rows=80))
