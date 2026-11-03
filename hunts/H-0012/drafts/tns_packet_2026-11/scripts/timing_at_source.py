"""TNS packet 2026-11: mean time of the NEOWISE exposures covering each source, per unWISE epoch.

As for OS-0030 (tns_validation/recompute_numbers.py, part 1): the unWISE epoch timestamp (header MJDMIN/MJDMAX
midpoint) is tile-wide, so query IRSA's NEOWISE-R single-exposure (L1b) frame index for every frame containing the
position and average the exposure times that fall in each epoch's visit. Tiles not cached locally have no headers
here, so frames are assigned to the epoch whose tile midpoint (from the h0012b light curves) is within 6 d; for M81
(tile 1507p696, fully cached) the header MJDMIN/MJDMAX and the n-m exposure count at the source are added.

    uv run python hunts/H-0012/drafts/tns_packet_2026-11/scripts/timing_at_source.py
Outputs: ~/oddsky-runs/imaging/scratch/tns-packet-2026-11/timing/
"""
import io
import json
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS

from oddsky.imaging import fetch

OUT = Path.home() / "oddsky-runs/imaging/scratch/tns-packet-2026-11/timing"
OUT.mkdir(parents=True, exist_ok=True)
RUNS = Path.home() / "oddsky-runs/h0012b"
IBE = "https://irsa.ipac.caltech.edu/ibe/search/wise/neowiser/p1bm_frm"
SRC = {
    "NGC4945_obs3": dict(ra=196.469723, dec=-49.416201, tile="1974m500", gal="NGC4945", gid=14),
    "M81_OS-0035": dict(ra=148.739293, dec=69.146800, tile="1507p696", gal="MESSIER081", gid=6),
}

summary = {}
for i, (lab, s) in enumerate(SRC.items()):
    if i:
        time.sleep(5)
    url = f"{IBE}?POS={s['ra']},{s['dec']}&ct=csv"
    try:
        r = requests.get(url, headers={"User-Agent": "curl/8.7.1"}, timeout=300)
        r.raise_for_status()
        text = r.text
        how = f"requests HTTP {r.status_code}"
    except requests.RequestException as e:  # python TLS to IRSA was reset once in the OS-0030 check; curl works
        text = subprocess.run(["curl", "-s", "-m", "300", url], capture_output=True, text=True, check=True).stdout
        how = f"curl after requests error {type(e).__name__}"
    frames = pd.read_csv(io.StringIO(text))
    frames.to_csv(OUT / f"l1b_frames_{lab}.csv", index=False)
    print(lab, "IRSA frames:", len(frames), how, url, flush=True)
    lc = pd.read_parquet(RUNS / s["tile"] / s["gal"] / "lightcurves.parquet")
    lc = lc[(lc.group == s["gid"])]
    rows = []
    for (ep, band), g in lc.groupby(["epoch", "band"]):
        mid = float(g.mjd.iloc[0])
        rec = dict(epoch=int(ep), band=int(band), tile_mid_mjd=mid)
        p = fetch.local_path(s["tile"], int(band), int(ep), "img-m")
        if p.exists():
            hdr = fits.getheader(p)
            lo, hi = float(hdr["MJDMIN"]), float(hdr["MJDMAX"])
            x, y = WCS(hdr).all_world2pix([[s["ra"], s["dec"]]], 0)[0]
            nmap = fits.getdata(fetch.local_path(s["tile"], int(band), int(ep), "n-m"))
            rec.update(tile_mjdmin=lo, tile_mjdmax=hi, n_m_at_source=int(nmap[int(round(y)), int(round(x))]))
            f = frames[(frames.band == band) & (frames.mjd_obs > lo - 0.5) & (frames.mjd_obs < hi + 0.5)]
        else:
            f = frames[(frames.band == band) & (np.abs(frames.mjd_obs - mid) < 6)]
        fq = f[f.qual_frame > 0]
        if len(f):
            rec.update(n_frames=len(f), n_frames_qual_gt0=len(fq),
                       mjd_first=float(f.mjd_obs.min()), mjd_last=float(f.mjd_obs.max()),
                       mjd_mean_qual=float(fq.mjd_obs.mean()) if len(fq) else None,
                       utc_mean_qual=Time(fq.mjd_obs.mean(), format="mjd").iso if len(fq) else None,
                       utc_first=Time(f.mjd_obs.min(), format="mjd").iso,
                       utc_last=Time(f.mjd_obs.max(), format="mjd").iso,
                       exptime_s=round(7.7 * len(fq), 1))
        else:
            rec.update(n_frames=0, note="no NEOWISE-R L1b frames (cryogenic/post-cryo 2010-11 epoch, or none)")
        rows.append(rec)
    tim = pd.DataFrame(rows).sort_values(["epoch", "band"])
    tim.to_csv(OUT / f"timing_{lab}.csv", index=False)
    pd.set_option("display.width", 250)
    print(tim.to_string(), flush=True)
    summary[lab] = tim.to_dict("records")
(OUT / "timing.json").write_text(json.dumps(summary, indent=1, default=str))
