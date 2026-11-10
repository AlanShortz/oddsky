"""Fetch, for each probed galaxy with repeat ACS/WFC F814W measurements, the bright end of the Hubble Source Catalog:
the summary rows (for colours) and every F814W detection, down to 1.3 mag below the predicted red-giant tip.

Usage: 03_fetch.py [min_count] [names...]   Resumable; data go to ~/oddsky-runs/h0019/hsc/<name>_{sum,det}.parquet
"""
import csv, sys, time, pathlib, traceback
import pandas as pd
from oddsky.data import hsc

RUN = pathlib.Path.home() / "oddsky-runs/h0019"
HERE = pathlib.Path(__file__).resolve().parents[1]
(RUN / "hsc").mkdir(exist_ok=True)
M_TIP, AB_VEGA, APCOR = -4.05, 0.43, 0.25   # tip in I (Vega); ACS F814W AB - Vega; 0.15" aperture -> total (approx.)
SUMCOLS = ["MatchID", "MatchRA", "MatchDec", "NumVisits", "NumFilters", "CI", "CI_Sigma", "Extinction", "StartMJD", "StopMJD"]
COLOUR = ["A_F814W", "A_F606W", "A_F555W", "A_F475W", "A_F435W", "W3_F814W", "W3_F606W", "W3_F555W", "W3_F475W", "W3_F110W",
          "W3_F160W", "W2_F814W", "W2_F606W", "W2_F555W"]


def probe_rows():
    seen = {}
    for part in sorted((HERE / "work").glob("probe*.csv")):
        for r in csv.DictReader(part.open()):
            if r["name"] not in seen or int(r["n2"]) > int(seen[r["name"]]["n2"]):
                seen[r["name"]] = r
    return list(seen.values())


def tip_pred(dist_mpc: float, ab_gal: float) -> float:
    import math
    return 5 * math.log10(dist_mpc * 1e5) + M_TIP + 0.42 * ab_gal + AB_VEGA + APCOR


def main():
    minc = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    only = set(sys.argv[2:])
    ab = {}
    for ln in (RUN / "cat/ungc.tsv").read_text().splitlines():
        p = [x.strip() for x in ln.split("\t")]
        if len(p) > 9 and not ln.startswith("#"):
            try:
                ab[p[0]] = float(p[9])
            except ValueError:
                pass
    for g in probe_rows():
        name = g["name"]; key = name.replace(" ", "_")
        if only and name not in only:
            continue
        if not only and int(g["A_F814W"] or 0) < minc:
            continue
        fs, fd = RUN / f"hsc/{key}_sum.parquet", RUN / f"hsc/{key}_det.parquet"
        if fd.exists():
            continue
        lim = tip_pred(float(g["dist"]), ab.get(name, 0.0)) + 1.3
        t = time.time()
        try:
            cols = SUMCOLS + [c for b in COLOUR for c in (b, b + "_N")]
            s = hsc.summary(float(g["ra"]), float(g["dec"]), float(g["radius"]), columns=cols, **{"A_F814W.lt": lim})
            d = hsc.visits(float(g["ra"]), float(g["dec"]), float(g["radius"]), "F814W", detector="ACS/WFC", mag_max=lim + 0.5)
        except Exception:  # noqa: BLE001
            print(name, "FAILED", traceback.format_exc()[-300:], flush=True)
            continue
        s.to_parquet(fs); d.to_parquet(fd)
        span = (d.StartMJD.max() - d.StartMJD.min()) if len(d) else 0
        print(f"{name:<16} lim={lim:.2f} sum={len(s)} det={len(d)} images={d.ImageID.nunique() if len(d) else 0} span={span:.0f}d [{time.time()-t:.0f}s]", flush=True)


main()
