"""Referee J193353: Gaia GOST transit forecast 2019-10-01 .. 2020-12-31 for J193353.06-211813.4.
POST GostServlet (multipart, session cookie), poll result.jsp, follow the export link (csv).
uv run python .../n6_gost.py ; raw pages to /tmp/j1933nov/gost/, csv to this review directory."""
import re, time
from pathlib import Path
import httpx

RA, DEC = 293.471115, -21.3037472
B = "https://gaia.esac.esa.int/gost/"
RAW = Path("/tmp/j1933nov/gost"); RAW.mkdir(parents=True, exist_ok=True)
OUTCSV = Path("hunts/H-0007/reviews/claude-referee-J193353-2026-10-29/gost_2019oct-2020dec.csv")
c = httpx.Client(timeout=120, follow_redirects=True, headers={"User-Agent": "oddsky/0.1 (open-source astronomy)"})
c.get(B + "index.jsp")
form = {"inputmode": "single", "serviceCode": "1", "srcname": "", "srcra": f"{RA}", "srcdec": f"{DEC}",
        "from": "2019-10-01T00:00:00", "to": "2020-12-31T23:59:59"}
r = c.post(B + "GostServlet", files={k: (None, v) for k, v in form.items()})
print("submit:", r.status_code, r.text.strip()[:300])
link = None
for i in range(40):
    time.sleep(6)
    page = c.get(B + "result.jsp").text
    (RAW / "result.html").write_text(page)
    rows = re.findall(r"<tr>(.*?)</tr>", page, flags=re.S)
    if rows:
        last = re.sub(r"<[^>]+>", " | ", rows[-1]); print("result row:", re.sub(r"\s+", " ", last)[:300])
    links = re.findall(r'href="(export\.jsp\?[^"]*format=csv)"', page, flags=re.I)
    if links:
        link = links[-1]; break
print("export link:", link)
if link:
    r = c.get(B + link.lstrip("/").removeprefix("gost/"))
    (RAW / "export_raw.csv").write_bytes(r.content)
    txt = r.text
    print("export status", r.status_code, "bytes", len(r.content))
    print(txt[:1500])
