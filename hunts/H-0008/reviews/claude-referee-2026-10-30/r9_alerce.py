"""r9: ALeRCE broker (public ZTF alert stream): objects within 5" of each target, with their light-curve classifier output."""
import json, os, sys, time
import requests
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from targets import TARGETS
for k, (name, ra, dec, t, pix) in TARGETS.items():
    try:
        r = requests.get("https://api.alerce.online/ztf/v1/objects/", params={"ra": ra, "dec": dec, "radius": 5, "page_size": 20}, timeout=60)
        items = r.json().get("items", [])
        print(name, f"HTTP {r.status_code}", "objects:", [(i["oid"], i.get("ndet"), i.get("firstmjd"), i.get("lastmjd"), i.get("class"), i.get("classifier")) for i in items])
        for i in items:
            c = requests.get(f"https://api.alerce.online/ztf/v1/objects/{i['oid']}/probabilities", timeout=60).json()
            top = sorted([x for x in c if x.get("ranking") == 1], key=lambda x: x["classifier_name"])
            print("   ", i["oid"], [(x["classifier_name"], x["class_name"], round(x["probability"], 2)) for x in top])
    except Exception as e:  # noqa: BLE001
        print(name, "UNKNOWN", e)
    time.sleep(2)
