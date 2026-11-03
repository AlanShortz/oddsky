"""H-0015 s3: Gaia's scanning law at every target, from GOST (https://gaia.esac.esa.int/gost/), over DR4's span.

GOST forecasts each field-of-view transit of a position: time at Gaia (UTC) and at the barycentre (BJD TCB), CCD row, scan
angle, across-scan field angle and the along/across-scan parallax factors. It ignores dead time and data loss (about 80% of
forecast transits reach the ground, per the GOST page), which s4/s5 model by dropping transits at random.

Same client as H-0009's p2_gost.py (POST GostServlet, poll result.jsp, follow the csv export link). One position at a time,
5 s polling, 3 s between targets. Raw exports go to ~/oddsky-runs/h0015/gost/gost_<source_id>.csv unchanged; failures are
listed in hunts/H-0015/data/gost_errors.jsonl. Already-fetched targets are skipped.

Run: uv run python -I hunts/H-0015/scripts/s3_gost.py [source_id ...]
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import httpx
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
D = ROOT / "hunts/H-0015/data"
OUT = Path.home() / "oddsky-runs/h0015/gost"
B = "https://gaia.esac.esa.int/gost/"
OB110462 = ("OB110462", 267.917458, -29.890639)


def fetch(name: str, ra: float, dec: float, t0="2014-07-25T10:32:00", t1="2020-01-21T00:00:00") -> str:
    c = httpx.Client(timeout=180, follow_redirects=True, headers={"User-Agent": "oddsky/0.3 (open-source astronomy)"})
    c.get(B + "index.jsp")
    form = {"inputmode": "single", "serviceCode": "1", "srcname": name, "srcra": f"{ra}", "srcdec": f"{dec}",
            "from": t0, "to": t1}
    r = c.post(B + "GostServlet", files={k: (None, v) for k, v in form.items()})
    if r.status_code >= 400:
        raise RuntimeError(f"submit HTTP {r.status_code}: {r.text[:200]}")
    if "error occured" in r.text or "error occurred" in r.text:
        raise RuntimeError(re.sub(r"<[^>]+>|\s+", " ", r.text).strip()[:300])
    for _ in range(72):
        time.sleep(5)
        page = c.get(B + "result.jsp").text
        links = re.findall(r'href="(export\.jsp\?[^"]*format=csv)"', page, flags=re.I)
        if links:
            r = c.get(B + links[-1].lstrip("/").removeprefix("gost/"))
            if r.status_code >= 400 or "ObservationTimeAtGaia" not in r.text:
                raise RuntimeError(f"export HTTP {r.status_code}: {r.text[:200]}")
            return r.text
    raise RuntimeError("no export link after 6 min")


def main(argv):
    OUT.mkdir(parents=True, exist_ok=True)
    g = pd.read_csv(D / "gaia_dr3.csv", dtype={"source_id": str})
    todo = [(r.source_id, r.ra, r.dec) for r in g.itertuples()] + [OB110462]
    if argv:
        todo = [x for x in todo if x[0] in argv]
    errs = []
    for name, ra, dec in todo:
        p = OUT / f"gost_{name}.csv"
        if p.exists() and p.stat().st_size > 500:
            continue
        try:
            txt = fetch(name, ra, dec)
            p.write_text(txt)
            print(name, "rows", txt.count("\n") - 1, flush=True)
        except Exception as e:  # noqa: BLE001  recorded, never treated as "no transits"
            errs.append({"source_id": name, "error": f"{type(e).__name__}: {e}"[:400]})
            print(name, "ERROR", e, flush=True)
        time.sleep(3)
    with open(D / "gost_errors.jsonl", "a") as f:
        for e in errs:
            f.write(json.dumps({**e, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")
    print(f"done; {len(errs)} errors")


if __name__ == "__main__":
    main(sys.argv[1:])
