"""Which nearby galaxies have stars the Hubble Source Catalog measured at least twice in one band?

Reads Karachentsev+2013 (UNGC) and, for each galaxy within DMAX Mpc, asks HSC v3 for up to 20,000 sources with two or
more visits. Counts per band are therefore lower bounds, good for ranking. Appends to work/probe.csv as it goes.
"""
import csv, io, sys, time, pathlib
import requests

RUN = pathlib.Path.home() / "oddsky-runs/h0019"
OUT = pathlib.Path(__file__).resolve().parents[1] / "work/probe.csv"
API = "https://catalogs.mast.stsci.edu/api/v0.1/hsc/v3/summary/magaper2.csv"
BANDS = ["A_F814W", "W3_F814W", "W2_F814W", "W3_F160W", "W3_F110W", "A_F606W"]
DMAX = float(sys.argv[1]) if len(sys.argv) > 1 else 4.5
CAP = 20000


def galaxies():
    rows = []
    for ln in (RUN / "cat/ungc.tsv").read_text().splitlines():
        if ln.startswith("#") or not ln.strip():
            continue
        p = [x.strip() for x in ln.split("\t")]
        try:
            h, m, sec = (float(x) for x in p[1].split())
            d, dm, ds = (float(x) for x in p[2].replace("-", "").replace("+", "").split())
            ra = 15 * (h + m / 60 + sec / 3600)
            dec = (-1 if p[2].startswith("-") else 1) * (d + dm / 60 + ds / 3600)
            a26, dist = float(p[3] or 1), float(p[4])
        except ValueError:
            continue
        if dist <= DMAX:
            rows.append(dict(name=p[0], ra=round(ra, 5), dec=round(dec, 5), a26=a26, dist=dist, f_dist=p[5], BMag=p[6], logLK=p[7], T=p[8]))
    return rows


def probe(g):
    rad = min(max(g["a26"] / 2 / 60, 0.025), 0.2)
    cols = ["MatchID", "StartMJD", "StopMJD"] + [b + "_N" for b in BANDS]
    params = {"ra": g["ra"], "dec": g["dec"], "radius": rad, "NumVisits.gte": 2, "columns": "[" + ",".join(cols) + "]",
              "pagesize": CAP}
    out = dict(g, radius=round(rad, 4), n2=-1)
    for attempt in range(3):
        try:
            r = requests.get(API, params=params, timeout=240)
            if r.status_code == 200:
                rows = list(csv.DictReader(io.StringIO(r.text)))
                out["n2"] = len(rows)
                out["span"] = round(max((float(x["StopMJD"]) - float(x["StartMJD"]) for x in rows), default=0))
                for b in BANDS:
                    out[b] = sum(1 for x in rows if x.get(b + "_N") and float(x[b + "_N"]) >= 2)
                return out
        except Exception as e:  # noqa: BLE001
            print("  retry", g["name"], repr(e)[:80], flush=True)
        time.sleep(5 * (attempt + 1))
    return out


if __name__ == "__main__":
    gs = galaxies()
    done = set()
    if OUT.exists() and OUT.stat().st_size:
        done = {r["name"] for r in csv.DictReader(OUT.open())}
    fields = ["name", "ra", "dec", "a26", "dist", "f_dist", "BMag", "logLK", "T", "radius", "n2", "span"] + BANDS
    f = OUT.open("a", newline="")
    w = csv.DictWriter(f, fieldnames=fields)
    if not done:
        w.writeheader()
    print(len(gs), "galaxies within", DMAX, "Mpc;", len(done), "done", flush=True)
    for g in gs:
        if g["name"] in done:
            continue
        t = time.time(); r = probe(g)
        w.writerow({k: r.get(k, 0) for k in fields}); f.flush()
        print(f"{g['name']:<18}{g['dist']:5.2f} n2={r['n2']} " + " ".join(f"{b}={r.get(b, 0)}" for b in BANDS if r.get(b, 0)) + f"  [{time.time()-t:.0f}s]", flush=True)
