"""Two points per star: the excess of large brightness changes among stars above the red-giant tip.

For each galaxy: place the tip, build one long-lag pair per star (first and last ACS/WFC F814W detection) and, where the
star has one, one short-lag pair (closest two detections, under 10 d); remove each image pair's zero-point offset; count
|dmag| > x in the AGB box and in the controls. Writes work/measure.csv, work/pairs/<name>.parquet.

    04_measure.py            all fetched galaxies
    04_measure.py --noise    short-lag statistics only (nothing about long-lag AGB pairs is computed or printed)
"""
import csv, sys, math, pathlib
import numpy as np, pandas as pd

RUN = pathlib.Path.home() / "oddsky-runs/h0019"
HERE = pathlib.Path(__file__).resolve().parents[1]
(HERE / "work/pairs").mkdir(parents=True, exist_ok=True)
M_TIP, AB_VEGA, APCOR = -4.05, 0.43, 0.25
LONG, SHORT = 100.0, 10.0          # days
CI_LO, CI_HI = 0.85, 1.30          # concentration index of a point source in ACS/WFC (WLM: median 1.06)
THRESH = (0.2, 0.3, 0.5)
# red if colour (AB) exceeds this; blue if below red - 0.35. Vega V-I ~ 1.05 at the cut.
RED = {"A_F606W": 0.45, "A_F555W": 0.62, "A_F475W": 1.07, "W3_F606W": 0.45, "W3_F555W": 0.62, "W3_F475W": 1.07}
RED_EBV = {"A_F606W": 1.0, "A_F555W": 1.3, "A_F475W": 2.1, "W3_F606W": 1.0, "W3_F555W": 1.3, "W3_F475W": 2.1}  # E(colour)/E(B-V)


def galaxies():
    ab = {}
    for ln in (RUN / "cat/ungc.tsv").read_text().splitlines():
        p = [x.strip() for x in ln.split("\t")]
        if len(p) > 9 and not ln.startswith("#"):
            try:
                ab[p[0]] = float(p[9])
            except ValueError:
                pass
    out = []
    for g in probe_rows():
        key = g["name"].replace(" ", "_")
        if (RUN / f"hsc/{key}_det.parquet").exists():
            g["AB"] = ab.get(g["name"], 0.0); g["key"] = key
            out.append(g)
    return out


def probe_rows():
    seen = {}
    for part in sorted((HERE / "work").glob("probe*.csv")):
        for r in csv.DictReader(part.open()):
            if r["name"] not in seen or int(r["n2"]) > int(seen[r["name"]]["n2"]):
                seen[r["name"]] = r
    return list(seen.values())


def tip_pred(g):
    return 5 * math.log10(float(g["dist"]) * 1e5) + M_TIP + 0.42 * g["AB"] + AB_VEGA + APCOR


def tip_edge(mag, pred):
    """Sobel edge of the luminosity function of red stars within 0.5 mag of the prediction; (edge, significance)."""
    bins = np.arange(pred - 1.5, pred + 1.3, 0.05)
    h, e = np.histogram(mag, bins=bins)
    hs = np.convolve(h, np.ones(3) / 3, mode="same")
    sob = np.zeros(len(h))
    sob[2:-2] = (hs[4:] + hs[3:-1] - hs[1:-3] - hs[:-4]) / np.sqrt(hs[4:] + hs[3:-1] + hs[1:-3] + hs[:-4] + 1)
    c = (e[:-1] + e[1:]) / 2
    ok = np.abs(c - pred) <= 0.5
    if not ok.any() or h.sum() < 200:
        return np.nan, 0.0
    i = np.argmax(np.where(ok, sob, -9))
    return float(c[i]), float(sob[i])


def star_pairs(det):
    """One long pair (first, last detection) and one short pair (closest in time, < SHORT d) per star."""
    d = det[(det.CI > CI_LO) & (det.CI < CI_HI) & (det.Flags == 0)].copy()
    d = d.groupby(["MatchID", "ImageID"], as_index=False).agg(mjd=("StartMJD", "mean"), mag=("MagAper2", "mean"), n=("MagAper2", "size"))
    d = d[d.n == 1].sort_values(["MatchID", "mjd"])
    g = d.groupby("MatchID")
    first, last = g.first(), g.last()
    lp = pd.DataFrame({"img1": first.ImageID, "img2": last.ImageID, "mjd1": first.mjd, "lag": last.mjd - first.mjd,
                       "mag1": first.mag, "mag2": last.mag})
    lp = lp[lp.lag >= LONG]
    d["dt"] = g.mjd.diff(); d["pmag"] = g.mag.shift(); d["pimg"] = g.ImageID.shift()
    s = d[(d.dt > 0) & (d.dt < SHORT)].sort_values("dt").groupby("MatchID").first()
    sp = pd.DataFrame({"img1": s.pimg.astype("int64"), "img2": s.ImageID, "mjd1": s.mjd - s.dt, "lag": s.dt, "mag1": s.pmag, "mag2": s.mag})
    out = []
    for kind, p in (("long", lp), ("short", sp)):
        p = p.copy(); p["kind"] = kind; p["mag"] = (p.mag1 + p.mag2) / 2; p["dmag"] = p.mag2 - p.mag1
        out.append(p.reset_index())
    return pd.concat(out, ignore_index=True)


def measure(g, noise_only=False):
    key = g["key"]
    det = pd.read_parquet(RUN / f"hsc/{key}_det.parquet"); summ = pd.read_parquet(RUN / f"hsc/{key}_sum.parquet")
    row = dict(name=g["name"], dist=float(g["dist"]), BMag=g["BMag"], logLK=g["logLK"], n_det=len(det))
    if not len(det) or not len(summ):
        return row, None
    pred = tip_pred(g)
    ccol = next((c for c in RED if c in summ and summ[c].notna().sum() > 0.3 * len(summ)), None)
    row["colour"] = ccol
    if ccol is None:
        return row, None
    ebv = g["AB"] / 4.1
    summ = summ.assign(col=summ[ccol] - summ["A_F814W"] - RED_EBV[ccol] * ebv)
    red_cut = RED[ccol]
    p = star_pairs(det).merge(summ[["MatchID", "MatchRA", "MatchDec", "col", "A_F814W", "NumVisits"]], on="MatchID", how="left")
    p["cls"] = np.where(p.col > red_cut, "red", np.where(p.col < red_cut - 0.35, "blue", "mid"))
    redstars = summ[(summ.col > red_cut) & (summ.CI.between(CI_LO, CI_HI))]
    edge, sig = tip_edge(redstars.A_F814W.values, pred)
    tip = edge if sig >= 4 else pred
    row.update(tip_pred=round(pred, 2), tip_edge=round(edge, 2) if edge == edge else None, tip_sig=round(sig, 1), tip=round(tip, 2))
    p["rel"] = p.mag - tip
    use = p.rel.between(-2.5, 1.0)
    npair = p[use].groupby(["kind", "img1", "img2"]).dmag.transform("size")
    zp = p[use].groupby(["kind", "img1", "img2"]).dmag.transform("median")
    p = p[use].assign(nimg=npair, d=p.dmag[use] - zp)
    p = p[p.nimg >= 30]
    p["box"] = np.select([(p.cls == "red") & p.rel.between(-1, 0, inclusive="left"), (p.cls == "red") & p.rel.between(-2, -1, inclusive="left"),
                          (p.cls == "red") & p.rel.between(0, 0.5, inclusive="right"), (p.cls == "blue") & p.rel.between(-2, 0, inclusive="left")],
                         ["agb", "agb_bright", "rgb", "blue"], "other")
    p.to_parquet(HERE / f"work/pairs/{key}.parquet")
    for kind in ("short", "long"):
        for box in ("agb", "agb_bright", "rgb", "blue"):
            if noise_only and kind == "long" and box.startswith("agb"):
                continue
            s = p[(p.kind == kind) & (p.box == box)]
            row[f"n_{kind}_{box}"] = len(s)
            if len(s):
                row[f"sd_{kind}_{box}"] = round(1.4826 * float(np.median(np.abs(s.d))), 4)
                for x in THRESH:
                    row[f"k{int(x*10):02d}_{kind}_{box}"] = int((np.abs(s.d) > x).sum())
        s = p[p.kind == kind]
        row[f"medlag_{kind}"] = round(float(s.lag.median()), 1) if len(s) else None
    return row, p


if __name__ == "__main__":
    noise_only = "--noise" in sys.argv
    rows = []
    for g in galaxies():
        r, _ = measure(g, noise_only)
        rows.append(r)
    df = pd.DataFrame(rows)
    df.to_csv(HERE / ("work/noise.csv" if noise_only else "work/measure.csv"), index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 60)
    cols = [c for c in ["name", "dist", "colour", "tip_pred", "tip_edge", "tip_sig", "medlag_long", "n_long_rgb", "n_long_blue", "n_short_agb",
                        "sd_short_agb", "k03_short_agb", "n_short_rgb", "sd_short_rgb", "k03_short_rgb", "sd_long_rgb", "k03_long_rgb", "k03_long_blue"] if c in df]
    print(df[cols].to_string(index=False))
