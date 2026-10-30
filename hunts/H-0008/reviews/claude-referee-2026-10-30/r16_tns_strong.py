"""r16: TNS cone search (10") for all 70 'strong unexplained' events (sky3_strong.csv), one request per 30 s, because the
investigators' tns column is empty for all 70 although three of them have TNS objects (r7). 429/errors = UNKNOWN.
Then, for each TNS hit, the object page (also 30 s apart) for the reporting group, internal name and remarks."""
import io, os, re, html, time
import pandas as pd, requests
HERE = os.path.dirname(os.path.abspath(__file__))
s = pd.read_csv(f"{HERE}/../../work/sky3_strong.csv", dtype={"g_source_id": str})
H = {"User-Agent": "Mozilla/5.0"}
out = []
for r in s.itertuples():
    res, objs = "", []
    try:
        q = requests.get("https://www.wis-tns.org/search", params={"ra": r.ra, "decl": r.dec, "radius": 10, "coords_unit": "arcsec", "format": "csv"}, headers=H, timeout=60)
        if q.status_code != 200:
            res = f"UNKNOWN (HTTP {q.status_code})"
        else:
            d = pd.read_csv(io.StringIO(q.text)) if q.text.strip() else pd.DataFrame()
            if "Name" not in d:
                res = "UNKNOWN (no Name column: " + q.text[:60].replace("\n", " ") + ")"
            elif d.empty:
                res = "none"
            else:
                objs = [n.replace("AT ", "").replace("SN ", "").strip() for n in d["Name"]]
                res = "; ".join(d["Name"])
    except Exception as e:  # noqa: BLE001
        res = f"UNKNOWN ({str(e)[:60]})"
    time.sleep(30)
    remarks = []
    for o in objs[:2]:
        try:
            p = requests.get(f"https://www.wis-tns.org/object/{o}", headers=H, timeout=60)
            t = html.unescape(re.sub(r"<[^>]+>", " | ", re.sub(r"<script.*?</script>", "", p.text, flags=re.S)))
            t = re.sub(r"(\s*\|\s*)+", " | ", t)
            i = t.find("Auto classification |")
            remarks.append(f"{o}: " + t[i + 22:i + 330].strip())
        except Exception as e:  # noqa: BLE001
            remarks.append(f"{o}: UNKNOWN {e}")
        time.sleep(30)
    print(r.designation, "->", res, "|", " || ".join(remarks), flush=True)
    out.append({"designation": r.designation, "tns": res, "tns_report": " || ".join(remarks)})
    pd.DataFrame(out).to_csv(f"{HERE}/r16_tns_strong.csv", index=False)
