"""The decisive check after the referee: the two-visit statistic from OGLE-III's real I-band light curves, not sinusoids.

Streams the OGLE-III long-period-variable photometry archive (nothing is unpacked to disk), and for every star of the Cloud
reference population draws pairs of real observations separated by each target lag (within 10%). Writes
~/oddsky-runs/h0019/ogle_pairs_<cloud>.parquet (star, lag, m1, m2).   Usage: 13_ogle_real.py lmc|smc
"""
import sys, tarfile, pathlib, urllib.request
import numpy as np, pandas as pd

CLOUD = sys.argv[1]
RUN = pathlib.Path.home() / "oddsky-runs/h0019"; HERE = pathlib.Path(__file__).resolve().parents[1]
URL = f"https://ftp.astrouw.edu.pl/ogle/ogle3/OIII-CVS/{CLOUD}/lpv/phot.tar.gz"
LAGS, NDRAW = (150, 400, 1000, 2500), 12
pop = pd.read_csv(HERE / f"work/{CLOUD}_population.csv", dtype={"star": str})
want = {s.strip().zfill(5) for s in pop.star.dropna() if s.strip()}
rng = np.random.default_rng(13); rows = []; seen = 0
with urllib.request.urlopen(URL, timeout=120) as resp, tarfile.open(fileobj=resp, mode="r|gz") as tar:
    for m in tar:
        if not m.isfile() or "/I/" not in m.name:
            continue
        star = m.name.rsplit("-", 1)[-1].split(".")[0]
        if star not in want:
            continue
        a = np.loadtxt(tar.extractfile(m), usecols=(0, 1, 2), ndmin=2)
        a = a[(a[:, 2] < 0.1) & (a[:, 1] > 5)]
        seen += 1
        if len(a) < 30:
            continue
        t, mag = a[:, 0], a[:, 1]
        for lag in LAGS:
            i = rng.integers(0, len(t), 400)
            j = np.searchsorted(t, t[i] + lag); ok = j < len(t)
            ok[ok] &= np.abs(t[j[ok]] - t[i[ok]] - lag) < 0.1 * lag
            for a1, a2 in zip(i[ok][:NDRAW], j[ok][:NDRAW]):
                rows.append((star, lag, mag[a1], mag[a2]))
        if seen % 2000 == 0:
            print(seen, "stars", len(rows), "pairs", flush=True)
df = pd.DataFrame(rows, columns=["star", "lag", "m1", "m2"])
df.to_parquet(RUN / f"ogle_pairs_{CLOUD}.parquet")
print(CLOUD, "done:", seen, "of", len(want), "stars found;", len(df), "pairs")
