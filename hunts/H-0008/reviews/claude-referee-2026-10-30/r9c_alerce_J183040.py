"""r9c: ALeRCE objects within 5" of J183040.98-220950.3 and their top classes; detections (sign of the difference flux)."""
import requests
ra, dec = 277.6707878, -22.1639838
r = requests.get("https://api.alerce.online/ztf/v1/objects/", params={"ra": ra, "dec": dec, "radius": 5, "page_size": 20}, timeout=60).json()
for i in r.get("items", []):
    det = requests.get(f"https://api.alerce.online/ztf/v1/objects/{i['oid']}/detections", timeout=60).json()
    pos = [round(d["mjd"], 1) for d in det if d.get("isdiffpos", 1) > 0]
    neg = [round(d["mjd"], 1) for d in det if d.get("isdiffpos", 1) < 0]
    print(i["oid"], "ndet", i.get("ndet"), "first", i.get("firstmjd"), "| positive:", pos[:30], "| negative:", len(neg))
    c = requests.get(f"https://api.alerce.online/ztf/v1/objects/{i['oid']}/probabilities", timeout=60).json()
    print("   ", [(x["classifier_name"], x["class_name"], round(x["probability"], 2)) for x in c if x.get("ranking") == 1])
if not r.get("items"):
    print("no ALeRCE object within 5\"")
