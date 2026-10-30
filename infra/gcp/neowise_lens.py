"""Sky pass "sky3lens" (hunt H-0008): an all-sky NEOWISE microlensing survey, one HEALPix pixel at a time.

Reads the NEOWISE-R single exposures exactly as the sky2 pass does (neowise_pixel_v2.py: same release files, same per-band
quality cuts, same visit medians), for every pixel including the Galactic plane, with two additions per visit:
  ccfrac  the share of the source's detections in that visit that carry a W1/W2 artifact flag (cc_flags D/P/H/O). Those frames
          are excluded from the medians, but a visit full of them is where latents and ghosts fake one-night brightenings.
  rchi    the median W1 PSF-fit reduced chi-square of the kept frames.
It then looks, star by star, for the H-0007 signature: a run of 1-3 consecutive visits brighter in BOTH bands by
>= max(0.2 mag, 6 sigma), achromatic (|dW1 - dW2| <= 0.1 + 0.15 |dW|), with every other visit within max(0.15 mag, 4 sigma),
on stars with >= 10 visits. The mirror (fainter) is recorded as the control. Outputs per pixel:
  events/pixel=N.parquet     one row per event, with the star's baseline, scatter and the event-visit diagnostics
  lightcurves/pixel=N.parquet  the visit light curves of event stars
  census/pixel=N.parquet     stars searched per 0.25-mag W1 bin and per scatter bin (for detection efficiency)
    python neowise_lens.py --out /mnt/disks/oddsky/runs/sky3lens --task-index 3 --pixels-per-task 60
"""

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.fs as pafs
import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from neowise_pixel_v2 import BUCKET, COLUMNS, RELEASES, VISIT_GAP, quality, s3  # noqa: E402

COLS = COLUMNS + ["w1rchi2"]


def _read_release(fs, pixel, rel):
    k0 = pixel >> 10
    path = f"{BUCKET}/{rel}/neowiser-healpix_k5-{rel}.parquet/healpix_k0={k0}/healpix_k5={pixel}/part0.snappy.parquet"
    try:
        pf = pq.ParquetFile(fs.open_input_file(path), pre_buffer=True)
    except (FileNotFoundError, OSError):
        return [], []
    frames, aw = [], []
    for batch in pf.iter_batches(batch_size=1_000_000, columns=COLS):
        batch = batch.filter(pc.and_(pc.is_valid(batch["allwise_cntr"]), pc.less(batch["r_allwise"], 2.0)))
        if batch.num_rows == 0:
            continue
        d = batch.to_pandas()
        q1, q2 = quality(d, "w1"), quality(d, "w2")
        cc = d["cc_flags"].astype(str).str.zfill(4)
        art = ((cc.str[0] != "0") | (cc.str[1] != "0")).to_numpy()
        keep = q1 | q2 | art
        frames.append(pd.DataFrame({
            "allwise_cntr": d["allwise_cntr"].to_numpy()[keep].astype("int64"),
            "mjd": d["mjd"].to_numpy()[keep],
            "w1": np.where(q1, d["w1mpro"], np.nan)[keep].astype("float32"),
            "w1e": d["w1sigmpro"].to_numpy()[keep].astype("float32"),
            "w2": np.where(q2, d["w2mpro"], np.nan)[keep].astype("float32"),
            "w2e": d["w2sigmpro"].to_numpy()[keep].astype("float32"),
            "art": art[keep],
            "rchi": np.where(q1, d["w1rchi2"], np.nan)[keep].astype("float32"),
        }))
        aw.append(d.groupby("allwise_cntr", sort=False)[["w1mpro_allwise", "w2mpro_allwise", "w3mpro_allwise",
                                                         "w4mpro_allwise"]].first())
        del d
    return frames, aw


def read_pixel(pixel, threads=4):
    from concurrent.futures import ThreadPoolExecutor
    fs = s3()
    frames, aw = [], []
    with ThreadPoolExecutor(threads) as ex:
        for f, a in ex.map(lambda rel: _read_release(fs, pixel, rel), RELEASES):
            frames += f
            aw += a
    if not frames:
        return pd.DataFrame(), pd.DataFrame()
    return pd.concat(frames, ignore_index=True), pd.concat(aw).groupby(level=0).first()


def visits(df):
    df = df.sort_values(["allwise_cntr", "mjd"], kind="mergesort", ignore_index=True)
    cn = df["allwise_cntr"].to_numpy(dtype="int64")  # int64 compare: see the sky1 merge bug
    new_src = np.r_[True, cn[1:] != cn[:-1]]
    gap = np.r_[False, np.diff(df["mjd"].to_numpy()) > VISIT_GAP]
    vid = np.cumsum(new_src | gap)
    df["vid"] = vid
    g = df.groupby("vid", sort=False)
    v = pd.DataFrame({"allwise_cntr": g["allwise_cntr"].first(), "t": g["mjd"].median(),
                      "w1": g["w1"].median(), "w1_n": g["w1"].count(), "w2": g["w2"].median(), "w2_n": g["w2"].count(),
                      "ccfrac": g["art"].mean(), "rchi": g["rchi"].median(),
                      "w1_sig": g["w1e"].median(), "w2_sig": g["w2e"].median()})
    for b in ("w1", "w2"):
        dev = (df[b] - v[b].reindex(df["vid"]).to_numpy()).abs()
        mad = dev.groupby(df["vid"], sort=False).median() * 1.4826
        n = v[f"{b}_n"].clip(lower=1)
        v[f"{b}_err"] = np.maximum(mad / np.sqrt(n), v[f"{b}_sig"] / np.sqrt(n)).clip(lower=0.005)
    v = v.drop(columns=["w1_sig", "w2_sig"]).reset_index(drop=True)
    return v[(v.w1_n >= 3) & (v.w2_n >= 3)].reset_index(drop=True)


def detect(v):
    v = v.sort_values(["allwise_cntr", "t"], kind="mergesort", ignore_index=True)
    g = v.groupby("allwise_cntr", sort=False)
    v["n"] = g["t"].transform("size")
    v = v[v.n >= 10].copy()
    g = v.groupby("allwise_cntr", sort=False)
    v["k"] = g.cumcount()
    for b in ("w1", "w2"):
        v[f"m{b}"] = g[b].transform("median")
        v[f"d{b}"] = v[b] - v[f"m{b}"]
        v[f"s{b}"] = np.maximum(1.4826 * v[f"d{b}"].abs().groupby(v["allwise_cntr"], sort=False).transform("median"), 0.02)
    rows = []
    for sign, kind in ((-1, "brighten"), (1, "fade")):
        hit = ((sign * v.dw1 >= np.maximum(0.2, 6 * v.sw1)) & (sign * v.dw2 >= np.maximum(0.2, 6 * v.sw2))
               & ((v.dw1 - v.dw2).abs() <= 0.1 + 0.15 * np.maximum(v.dw1.abs(), v.dw2.abs())))
        calm = (v.dw1.abs() <= np.maximum(0.15, 4 * v.sw1)) & (v.dw2.abs() <= np.maximum(0.15, 4 * v.sw2))
        v["hit"], v["calm"] = hit, calm
        s = v.groupby("allwise_cntr", sort=False).agg(nh=("hit", "sum"), nc=("calm", "sum"), n=("n", "first"))
        cand = s[(s.nh >= 1) & (s.nh <= 3) & (s.nh + s.nc == s.n)].index
        for cntr in cand:
            st = v[v.allwise_cntr == cntr]
            k = st.k[st.hit].to_numpy()
            if k[-1] - k[0] + 1 != len(k):
                continue
            e, o = st[st.hit], st[~st.hit]
            j = int(np.argmax(np.abs(e.dw1.to_numpy())))
            rows.append({"allwise_cntr": int(cntr), "kind": kind, "n_visits": int(st.n.iloc[0]), "nhit": len(k),
                         "edge": bool(k[0] == 0 or k[-1] == st.n.iloc[0] - 1), "t": float(e.t.iloc[j]),
                         "dw1": float(e.dw1.iloc[j]), "dw2": float(e.dw2.iloc[j]), "w1_med": float(st.mw1.iloc[0]),
                         "w2_med": float(st.mw2.iloc[0]), "sw1": float(st.sw1.iloc[0]), "sw2": float(st.sw2.iloc[0]),
                         "ccfrac_event": float(e.ccfrac.max()), "ccfrac_other": float(o.ccfrac.median()),
                         "rchi_ratio": float(e.rchi.median() / max(o.rchi.median(), 1e-3))})
    census = v.drop_duplicates("allwise_cntr")[["mw1", "sw1"]]
    census = census.assign(w1bin=(census.mw1 * 4).round() / 4, sbin=np.minimum((census.sw1 * 100).round() / 100, 0.3))
    census = census.groupby(["w1bin", "sbin"]).size().rename("n").reset_index()
    return pd.DataFrame(rows), census, v


def process(pixel, base, fs):
    t0 = time.time()
    raw, allwise = read_pixel(pixel)
    if raw.empty:
        rep = {"pixel": pixel, "status": "empty"}
    else:
        v = visits(raw)
        ev, census, vv = detect(v)
        if len(ev):
            ev = ev.merge(allwise.reset_index(), on="allwise_cntr", how="left")
        ev["pixel"] = pixel
        census["pixel"] = pixel
        lc = v[v.allwise_cntr.isin(set(ev.allwise_cntr))].assign(pixel=pixel) if len(ev) else v.iloc[:0]
        for name, tab in (("events", ev), ("census", census), ("lightcurves", lc)):
            pq.write_table(pa.Table.from_pandas(tab, preserve_index=False), f"{base}/{name}/pixel={pixel}.parquet", filesystem=fs)
        rep = {"pixel": pixel, "status": "ok", "rows": int(len(raw)), "stars": int(vv.allwise_cntr.nunique()),
               "events": int(len(ev)), "s": round(time.time() - t0, 1)}
    with fs.open_output_stream(f"{base}/reports/pixel={pixel}.json") as fh:
        fh.write(json.dumps(rep).encode())
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("pixels", nargs="*", type=int)
    ap.add_argument("--out", required=True)
    ap.add_argument("--task-index", type=int, default=int(os.environ.get("BATCH_TASK_INDEX", "-1")))
    ap.add_argument("--pixels-per-task", type=int, default=60)
    ap.add_argument("--pixel-list", default=None, help="file with pixels to process (default: all 12288)")
    a = ap.parse_args(argv)
    allpix = [int(x) for x in open(a.pixel_list).read().split()] if a.pixel_list else list(range(12288))
    pixels = a.pixels or allpix[a.task_index * a.pixels_per_task:(a.task_index + 1) * a.pixels_per_task]
    fs, base = (pafs.FileSystem.from_uri(a.out) if "://" in a.out else (pafs.LocalFileSystem(), a.out))
    for d in ("events", "census", "lightcurves", "reports"):
        fs.create_dir(f"{base}/{d}", recursive=True)
    for p in pixels:
        if fs.get_file_info(f"{base}/reports/pixel={p}.json").type == pafs.FileType.File:
            continue
        try:
            print(json.dumps(process(p, base, fs)), flush=True)
        except Exception as e:  # noqa: BLE001
            print(json.dumps({"pixel": p, "status": "error", "error": str(e)[:300]}), flush=True)


if __name__ == "__main__":
    main()
