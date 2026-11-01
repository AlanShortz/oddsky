"""r7: novelty of the 21 candidates, from sources other than the investigators' merged reference file.
Every failed lookup is printed as UNKNOWN, never as 'nothing'.
  1 OGLE EWS public lenses.par files 2014-2017 (www.astrouw.edu.pl): nearest event, events within 15' (footprint proxy)
  2 KMTNet 2015 public event page (kmtnet.kasi.re.kr/~ulens/event/2015/; 2015 season, prime fields) and the local KMT 2016-24 list
  3 MOA alerts 2014-2017 (moaprime.massey.ac.nz): rows parsed
  4 Gaia Science Alerts live csv (gsaweb), any date within 60"
  5 Mroz+2020 OGLE GVS disc events (local copy), Mroz+2019 (investigators' match file is not reused; VizieR J/ApJS/244/29 queried)
  6 VSX (VizieR B/vsx/vsx; idia mirror, CDS fallback) within 10"; ASAS-SN variables (II/366) within 10"; ASAS-SN transients page
  7 SIMBAD (CfA) within 10"
  8 VizieR: every catalogue with a row within 1.5" (astroquery, CDS), titles listed if they mention variab/microlens/transient/YSO/
    emission/H-alpha/Be
Writes data/novelty.csv. Run: uv run python -I hunts/H-0010/reviews/claude-referee-2026-11-01/r7_novelty.py"""
import io, os, re, time
import numpy as np, pandas as pd, requests
from astropy.time import Time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
C = pd.read_csv(os.path.join(HERE, "data", "candidates21.csv"), dtype={"source_id": str})
UA = {"User-Agent": "Mozilla/5.0 (oddsky referee)"}
CACHE = os.path.join(HERE, "data", "novelty_cache")
os.makedirs(CACHE, exist_ok=True)


def sep(ra, dec, ra0, dec0):  # arcsec
    ra, dec, ra0, dec0 = map(np.radians, (ra, dec, ra0, dec0))
    s = np.sin((dec - dec0) / 2) ** 2 + np.cos(dec) * np.cos(dec0) * np.sin((ra - ra0) / 2) ** 2
    return np.degrees(2 * np.arcsin(np.sqrt(s))) * 3600


def get(url, name, **kw):
    p = os.path.join(CACHE, name)
    if os.path.exists(p):
        return open(p).read()
    r = requests.get(url, headers=UA, timeout=180, **kw)
    r.raise_for_status()
    open(p, "w").write(r.text)
    return r.text


def hms(s, deg=False):
    a = [float(x) for x in re.split("[: ]+", s.strip())]
    sg = -1 if s.strip().startswith("-") else 1
    v = abs(a[0]) + a[1] / 60 + a[2] / 3600
    return sg * v * (1 if deg else 15)


res = {c.name: {} for c in C.itertuples()}

print("== 1 OGLE EWS lenses.par 2014-2017")
og = []
for y in (2014, 2015, 2016, 2017):
    try:
        t = get(f"https://www.astrouw.edu.pl/ogle/ogle4/ews/{y}/lenses.par", f"ogle_{y}.par")
        for ln in t.splitlines()[1:]:
            f = ln.split()
            if len(f) > 7:
                try:
                    og.append((f"OGLE-{f[0]}", hms(f[3]), hms(f[4], True), float(f[5]) - 2400000.5 if f[5] != "-" else np.nan,
                               float(f[7]) if f[7] != "-" else np.nan))
                except ValueError:
                    pass
        print(f" {y}: {sum(1 for o in og if o[0].startswith(f'OGLE-{y}'))} events")
    except Exception as e:  # noqa: BLE001
        print(f" {y}: UNKNOWN ({e})")
og = pd.DataFrame(og, columns=["name", "ra", "dec", "t0", "tE"])
for c in C.itertuples():
    s = sep(og.ra.values, og.dec.values, c.ra, c.dec)
    i = int(np.argmin(s))
    res[c.name]["ogle_nearest"] = f"{og.name[i]} {s[i]/60:.1f}' (t0 {Time(og.t0[i], format='mjd').iso[:10]})"
    res[c.name]["ogle_15"] = int((s < 900).sum())
    res[c.name]["ogle_3as"] = ";".join(og.name[s < 3]) or "none"

print("== 2 KMTNet 2015 (public page) + local 2016-24")
try:
    t = get("https://kmtnet.kasi.re.kr/~ulens/event/2015/", "kmt2015.html")
    rows = re.findall(r"event=(KMT-2015-BLG-\d+)'.*?</tr>", t, re.S)
    kt = []
    for m in re.finditer(r"<tr align=center>(.*?)</tr>", t, re.S):
        cells = [re.sub("<.*?>|&nbsp;", "", x).strip() for x in re.findall(r"<td.*?>(.*?)</td>", m.group(1), re.S)]
        if len(cells) >= 10 and cells[0].startswith("KMT-2015"):
            kt.append((cells[0], hms(cells[8]), hms(cells[9], True), float(cells[4]) + 2450000 - 2400000.5, cells[3]))
    kt = pd.DataFrame(kt, columns=["name", "ra", "dec", "t0", "cls"])
    print(f" KMT 2015: {len(kt)} events parsed; RA {kt.ra.min():.2f}-{kt.ra.max():.2f}, Dec {kt.dec.min():.2f}-{kt.dec.max():.2f}")
except Exception as e:  # noqa: BLE001
    kt = pd.DataFrame(columns=["name", "ra", "dec", "t0", "cls"])
    print(" KMT 2015: UNKNOWN", e)
kl = pd.read_csv(os.path.join(REPO, "hunts/H-0008/ext/kmt_events.csv"))
for c in C.itertuples():
    for lab, k in (("kmt2015", kt), ("kmt16_24", kl)):
        if len(k) == 0:
            res[c.name][lab] = "UNKNOWN"; continue
        s = sep(k.ra.values.astype(float), k.dec.values.astype(float), c.ra, c.dec)
        i = int(np.argmin(s))
        res[c.name][lab] = f"nearest {k.name.iloc[i]} {s[i]/60:.1f}'; {(s < 900).sum()} within 15'; within 3\": {';'.join(k.name[s < 3]) or 'none'}"

print("== 3 MOA alerts")
for y in (2014, 2015, 2016, 2017):
    try:
        t = get(f"https://moaprime.massey.ac.nz/alerts/index/moa/{y}", f"moa_{y}.html")
        n = len(re.findall(r"<tr>\s*<td", t))
        print(f" MOA {y}: HTTP 200, {n} table rows in <tbody> (empty page = MOA's public alert index is not served)")
    except Exception as e:  # noqa: BLE001
        print(f" MOA {y}: UNKNOWN ({e})")

print("== 4 Gaia alerts (live)")
try:
    t = get("https://gsaweb.ast.cam.ac.uk/alerts/alerts.csv", "gaia_alerts.csv")
    a = pd.read_csv(io.StringIO(t), skipinitialspace=True)
    a.columns = [x.strip("# ") for x in a.columns]
    print(f" {len(a)} alerts, {a.Date.min()} .. {a.Date.max()}")
    for c in C.itertuples():
        s = sep(a.RaDeg.values, a.DecDeg.values, c.ra, c.dec)
        res[c.name]["gaia_alert_60as"] = "; ".join(f"{a.Name.iloc[i]} {a.Date.iloc[i][:10]} {s[i]:.0f}\"" for i in np.where(s < 60)[0]) or "none"
except Exception as e:  # noqa: BLE001
    print(" UNKNOWN", e)

print("== 5 OGLE GVS (Mroz+2020, local) and Mroz+2019 (VizieR)")
gv = pd.read_csv(os.path.join(REPO, "hunts/H-0008/ext/ogle_gvs_mroz2020.csv"))
for c in C.itertuples():
    s = sep(gv.ra.values, gv.dec.values, c.ra, c.dec)
    res[c.name]["gvs"] = f"nearest {s.min()/60:.1f}'" + (f" MATCH {gv.name[np.argmin(s)]}" if s.min() < 3 else "")

VIZ = ["https://vizier.idia.ac.za/viz-bin/asu-tsv", "https://vizier.idia.ac.za/viz-bin/asu-tsv"]  # CDS unreachable on 2026-11-01 (connect timeouts); idia tried twice


def viz(cat, ra, dec, r):
    last = ""
    for base in VIZ:
        try:
            q = requests.get(base, params={"-source": cat, "-c": f"{ra} {dec}", "-c.rs": r, "-out": "**", "-out.add": "_r",
                                           "-out.max": 20}, headers=UA, timeout=120, allow_redirects=True)
            if q.status_code != 200 or "#INFO" not in q.text:
                last = f"HTTP {q.status_code} via {base.split('/')[2]}"; continue
            lines = [ln for ln in q.text.splitlines() if ln and not ln.startswith("#")]
            if len(lines) < 3:
                return pd.DataFrame(), f"ok ({base.split('/')[2]})"
            return pd.read_csv(io.StringIO("\n".join([lines[0]] + lines[3:])), sep="\t"), f"ok ({base.split('/')[2]})"
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__} via {base.split('/')[2]}"
    return None, "UNKNOWN " + last


print("== 5b/6 VizieR: Mroz+2019, VSX, ASAS-SN variables, KMTNet 2015 (Kim+2018), VVV microlensing (Husseiniova+2021, Navarro+)")
cats = {"mroz2019": "J/ApJS/244/29", "mroz2020_gvs": "J/ApJS/249/16", "vsx": "B/vsx/vsx", "asassn_var": "II/366",
        "vivace_vvv_var": "J/MNRAS/509/2566", "navarro2020_vvv_ml": "J/ApJ/889/56"}
# (KMTNet 2015, Kim+2018, is not on VizieR: the public KMTNet 2015 page is used in part 2; Husseiniova+2021's VizieR id was not found)
for c in C.itertuples():
    for lab, cat in cats.items():
        r = 10 if lab in ("vsx", "asassn_var") else 3
        d, st = viz(cat, c.ra, c.dec, r)
        res[c.name][lab] = (st if d is None else ("none" if d.empty else "; ".join(
            " ".join(f"{k}={v}" for k, v in row.items() if k in ("_r", "Name", "Type", "ID", "Event", "Field", "Star", "tE", "t0", "Per", "Class", "OGLE"))
            or str(row.to_dict())[:150] for row in d.to_dict("records")[:3])) + f" [{st}]")
    print(c.name, {k: res[c.name][k][:90] for k in cats}, flush=True)

print("== 6b ASAS-SN transients page")
try:
    t = get("https://www.astronomy.ohio-state.edu/asassn/transients.html", "asassn_transients.html")
    co = re.findall(r"<td>\s*(\d\d:\d\d:\d\d\.\d+)\s*</td>\s*<td>\s*([+-]\d\d:\d\d:\d\d\.\d+)\s*</td>", t)
    print(f" {len(co)} coordinate pairs parsed")
    if co:
        ar = np.array([hms(x) for x, _ in co]); de = np.array([hms(y, True) for _, y in co])
        for c in C.itertuples():
            s = sep(ar, de, c.ra, c.dec)
            res[c.name]["asassn_transient_60as"] = f"{(s < 60).sum()} within 60\" (nearest {s.min():.0f}\")"
except Exception as e:  # noqa: BLE001
    print(" UNKNOWN", e)

print("== 7 SIMBAD (CfA TAP) 10\"")
for c in C.itertuples():
    q = (f"SELECT b.main_id, b.otype, b.sp_type, b.nbref, DISTANCE(POINT('ICRS', b.ra, b.dec), POINT('ICRS', {c.ra}, {c.dec}))*3600 AS sep "
         f"FROM basic AS b WHERE CONTAINS(POINT('ICRS', b.ra, b.dec), CIRCLE('ICRS', {c.ra}, {c.dec}, {10/3600})) = 1 ORDER BY sep")
    try:
        r = requests.post("https://simbad.cfa.harvard.edu/simbad/sim-tap/sync", data=dict(request="doQuery", lang="adql", format="csv", query=q),
                          headers=UA, timeout=120)
        r.raise_for_status()
        d = pd.read_csv(io.StringIO(r.text))
        res[c.name]["simbad"] = "; ".join(f"{x.main_id}|{x.otype}|{x.sp_type if isinstance(x.sp_type, str) else ''}|refs {x.nbref}|{x.sep:.1f}\""
                                         for x in d.itertuples()) or "none"
    except Exception as e:  # noqa: BLE001
        res[c.name]["simbad"] = f"UNKNOWN {e}"
    time.sleep(1)

print("== 8 VizieR-wide cone (all catalogues): NOT RUN -- CDS VizieR unreachable (connect timeouts) on 2026-11-01")

out = pd.DataFrame.from_dict(res, orient="index")
out.to_csv(os.path.join(HERE, "data", "novelty.csv"))
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 120)
for name, r in out.iterrows():
    print("\n" + name)
    for k, v in r.items():
        print(f"   {k}: {v}")
