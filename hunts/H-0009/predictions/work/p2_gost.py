"""p2: Gaia GOST scanning-law forecast (https://gaia.esac.esa.int/gost/) for each target, 2014-07-25..2020-01-20 (the DR4
span). POST GostServlet (multipart, session cookie), poll result.jsp, follow the csv export link. Raw exports are written
to work/gost/gost_<k>.csv unchanged. Usage: uv run python hunts/H-0009/predictions/work/p2_gost.py [k ...]"""
import os
import re
import sys
import time

import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from targets import HERE, T  # noqa: E402

B = "https://gaia.esac.esa.int/gost/"
OUT = os.path.join(HERE, "gost")
os.makedirs(OUT, exist_ok=True)


def fetch(k, ra, dec, t0="2014-07-25T10:32:00", t1="2020-01-21T00:00:00"):
    c = httpx.Client(timeout=180, follow_redirects=True, headers={"User-Agent": "oddsky/0.1 (open-source astronomy)"})
    c.get(B + "index.jsp")
    form = {"inputmode": "single", "serviceCode": "1", "srcname": k, "srcra": f"{ra}", "srcdec": f"{dec}", "from": t0, "to": t1}
    r = c.post(B + "GostServlet", files={kk: (None, v) for kk, v in form.items()})
    print(k, "submit:", r.status_code, re.sub(r"\s+", " ", r.text.strip())[:200])
    for _ in range(60):
        time.sleep(5)
        page = c.get(B + "result.jsp").text
        links = re.findall(r'href="(export\.jsp\?[^"]*format=csv)"', page, flags=re.I)
        if links:
            r = c.get(B + links[-1].lstrip("/").removeprefix("gost/"))
            p = os.path.join(OUT, f"gost_{k}.csv")
            open(p, "wb").write(r.content)
            print(k, "export", r.status_code, len(r.content), "bytes ->", p, "rows", r.text.count("\n") - 1)
            return True
    print(k, "no export link")
    return False


for k in sys.argv[1:] or list(T):
    t = T[k]
    fetch(k, t["ra"], t["dec"])
