"""Sky pass "sky2keep" (hunt H-0007): NEOWISE visit light curves for a fixed list of stars, one HEALPix pixel at a time.

Same reader, quality cuts and visit medians as the sky2 pass (neowise_pixel_v2.py, the fixed oddsky.sky.neowise_pixel), but it
keeps the light curves of the AllWISE sources listed in KEEP (csv: allwise_cntr,pixel) instead of applying the sky2 storage rule
(W1 < 13 and W2 peak-to-peak >= 0.3). Used for the W1 13-15 candidates, whose light curves sky2 did not store.
    python neowise_keep.py --keep /mnt/disks/oddsky/code/keep_h0007.csv --out /mnt/disks/oddsky/runs/sky2keep --task-index 3 --pixels-per-task 40
"""

import argparse
import json
import os
import sys
import time

import pandas as pd
import pyarrow as pa
import pyarrow.fs as pafs
import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from neowise_pixel_v2 import read_pixel, visits  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("pixels", nargs="*", type=int)
    ap.add_argument("--keep", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--task-index", type=int, default=int(os.environ.get("BATCH_TASK_INDEX", "-1")))
    ap.add_argument("--pixels-per-task", type=int, default=40)
    a = ap.parse_args(argv)
    keep = pd.read_csv(a.keep)
    by_pix = keep.groupby("pixel").allwise_cntr.apply(set).to_dict()
    allpix = sorted(by_pix)
    pixels = a.pixels or allpix[a.task_index * a.pixels_per_task:(a.task_index + 1) * a.pixels_per_task]
    fs, base = (pafs.FileSystem.from_uri(a.out) if "://" in a.out else (pafs.LocalFileSystem(), a.out))
    for d in ("lightcurves", "reports"):
        fs.create_dir(f"{base}/{d}", recursive=True)
    for p in pixels:
        rep_path = f"{base}/reports/pixel={p}.json"
        if fs.get_file_info(rep_path).type == pafs.FileType.File:
            print(json.dumps({"pixel": p, "status": "done-before"}), flush=True)
            continue
        t0 = time.time()
        raw, _, st = read_pixel(p)
        v = visits(raw) if not raw.empty else raw
        lc = v[v.allwise_cntr.isin(by_pix.get(p, set()))].assign(pixel=p) if len(v) else v
        pq.write_table(pa.Table.from_pandas(lc, preserve_index=False), f"{base}/lightcurves/pixel={p}.parquet", filesystem=fs)
        rep = {"pixel": p, "status": "ok", "wanted": len(by_pix.get(p, ())), "found": int(lc.allwise_cntr.nunique()) if len(lc) else 0,
               "rows": int(len(lc)), "s": round(time.time() - t0, 1), **st}
        with fs.open_output_stream(rep_path) as fh:
            fh.write(json.dumps(rep).encode())
        print(json.dumps(rep), flush=True)


if __name__ == "__main__":
    main()
