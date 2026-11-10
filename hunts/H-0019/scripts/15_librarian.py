"""Is any of the single-star candidates already known? The Librarian (SIMBAD, NED, ADS, VSX, shelves) on each of the
stars in work/candidates.csv, 1 arcsec radius, plus Yuan+2017 for M33 (offset removed, 0.2 arcsec).

Resumable; writes work/candidates_librarian.csv.   Usage: 15_librarian.py
"""
import csv, json, pathlib, time
import numpy as np, pandas as pd
from oddsky.librarian import prior_art

RUN = pathlib.Path.home() / "oddsky-runs/h0019"; HERE = pathlib.Path(__file__).resolve().parents[1]
OUT = HERE / "work/candidates_librarian.csv"
C = pd.read_csv(HERE / "work/candidates.csv")
off = json.loads((HERE / "work/rediscovery_m33.json").read_text())["offset_arcsec"]   # Hubble minus Yuan
y = []
for ln in (RUN / "cat/m33_yuan2017.tsv").read_text().splitlines():
    q = [x.strip() for x in ln.split("\t")]
    if not ln.startswith("#") and len(q) >= 7 and q[0][:2].isdigit():
        y.append((q[0], float(q[1]), float(q[2]), float(q[3]), float(q[5])))
y = pd.DataFrame(y, columns=["id", "ra", "dec", "per", "amp"])
done = set()
if OUT.exists():
    done = {int(r["MatchID"]) for r in csv.DictReader(OUT.open())}
f = OUT.open("a", newline=""); w = csv.writer(f)
if not done:
    w.writerow(["gal", "MatchID", "ra", "dec", "d", "verdict", "complete", "simbad", "simbad_otype", "ned", "catalogues", "n_topical", "yuan2017", "yuan_period", "summary"])
for r in C.itertuples():
    if int(r.MatchID) in done:
        continue
    yid, yper = "", ""
    if r.gal == "MESSIER033":
        cd = np.cos(np.radians(r.MatchDec))
        sep = np.hypot((y.ra + off[0] / 3600 / cd - r.MatchRA) * cd, y.dec + off[1] / 3600 - r.MatchDec) * 3600
        if sep.min() < 0.2:
            yid, yper = y.id[sep.idxmin()], y.per[sep.idxmin()]
    try:
        p = prior_art(float(r.MatchRA), float(r.MatchDec), 1.0, topics="transient")
        so = (p.get("simbad") or {}).get("object") or {}
        no = (p.get("ned") or {}).get("object") or {}
        row = [p.get("verdict"), p.get("complete"), so.get("main_id") or so.get("name") or "", so.get("otype") or "", no.get("name") or no.get("prefname") or "",
               ";".join(str(h.get("catalogue") or h.get("key") or h) for h in (p.get("catalogue_hits") or []))[:120], len(p.get("topical_papers") or []), yid, yper,
               " ".join(str(p.get("summary", "")).split())[:300]]
    except Exception as e:  # noqa: BLE001
        row = ["error", False, "", "", "", "", 0, yid, yper, repr(e)[:200]]
    w.writerow([r.gal, int(r.MatchID), r.MatchRA, r.MatchDec, r.d] + row); f.flush()
    print(r.gal, int(r.MatchID), row[0], row[2], row[3], yid, flush=True)
    time.sleep(0.5)
print("LIBRARIAN_DONE")
