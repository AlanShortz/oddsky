"""One HEALPix pixel of the NEOWISE-R single-exposure table -> per-star infrared light curves and features.

Reads IRSA's Parquet copy on AWS (anonymous, us-west-2) for every NEOWISE year, keeps only the columns
needed (~11% of the bytes), groups detections by their AllWISE source (`allwise_cntr`, no cross-match
needed), applies the standard quality cuts, collapses each ~1-day visit to a robust median, and
computes features for every star. The flagship feature is the *infrared afterglow* signature:
a star that was photospheric for its first visits, then brightened in W2 and reddened in W1-W2 for
two or more consecutive visits (what ASASSN-21qj did in 2018).

    python -m oddsky.sky.neowise_pixel 9840 --out /tmp/sky          # one pixel, local
    python -m oddsky.sky.neowise_pixel --task-index 7 --pixels-per-task 48 --out gs://bucket/run1
"""

from __future__ import annotations

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

BUCKET = "nasa-irsa-wise/wise/neowiser/catalogs/p1bs_psd/healpix_k5"
RELEASES = [f"year{i}" for i in range(1, 12)] + ["addendum"]
COLUMNS = ["allwise_cntr", "r_allwise", "mjd", "w1mpro", "w1sigmpro", "w2mpro", "w2sigmpro", "w1snr", "w2snr",
           "qual_frame", "qi_fact", "saa_sep", "moon_masked", "cc_flags", "ph_qual", "nb", "w1sat", "w2sat",
           "sso_flg", "w1mpro_allwise", "w2mpro_allwise", "w3mpro_allwise", "w4mpro_allwise"]
VISIT_GAP = 30.0       # days between NEOWISE visits (~6 months) vs within a visit (~1-2 days)
N_BASE = 3             # visits defining "before"
SAT = {"w1": 8.0, "w2": 7.0}


def s3() -> pafs.S3FileSystem:
    return pafs.S3FileSystem(anonymous=True, region="us-west-2", connect_timeout=30, request_timeout=120)


def quality(df: pd.DataFrame, band: str) -> np.ndarray:
    """Standard single-exposure cuts (Explanatory Supplement), per band. cc_flags is 4 chars (W1..W4);
    ph_qual and moon_masked are 2 chars (W1, W2)."""
    i = 0 if band == "w1" else 1
    cc = df["cc_flags"].astype(str)
    ph = df["ph_qual"].astype(str)
    mm = df["moon_masked"].astype(str)
    m = df[f"{band}mpro"]
    return ((df["qual_frame"] > 0) & (df["qi_fact"] > 0) & (df["saa_sep"] > 0)
            & (mm.str[i] == "0") & (cc.str[i] == "0") & (ph.str[i].isin(["A", "B"]))
            & (df["nb"] == 1) & (df[f"{band}sat"].fillna(1) < 0.05) & (df["sso_flg"].fillna(1) == 0)
            & np.isfinite(m) & (m > SAT[band])).to_numpy()


def _read_release(fs, pixel: int, rel: str) -> tuple[list, list, dict]:
    k0 = pixel >> 10
    path = f"{BUCKET}/{rel}/neowiser-healpix_k5-{rel}.parquet/healpix_k0={k0}/healpix_k5={pixel}/part0.snappy.parquet"
    frames, aw, st = [], [], {"bytes_read": 0, "rows_raw": 0, "releases": 0}
    try:
        pf = pq.ParquetFile(fs.open_input_file(path), pre_buffer=True)
    except (FileNotFoundError, OSError):
        return frames, aw, st
    md = pf.metadata
    idx = {md.schema.column(i).name: i for i in range(md.num_columns)}
    for rg in range(md.num_row_groups):
        st["bytes_read"] += sum(md.row_group(rg).column(idx[c]).total_compressed_size for c in COLUMNS)
    st["releases"] = 1
    # Stream in batches: the densest pixels hold hundreds of millions of detections.
    for batch in pf.iter_batches(batch_size=1_000_000, columns=COLUMNS):
        st["rows_raw"] += batch.num_rows
        # Keep detections associated with an AllWISE source within 2" (pre-existing objects only).
        batch = batch.filter(pc.and_(pc.is_valid(batch["allwise_cntr"]), pc.less(batch["r_allwise"], 2.0)))
        if batch.num_rows == 0:
            continue
        d = batch.to_pandas()
        q1, q2 = quality(d, "w1"), quality(d, "w2")
        keep = q1 | q2
        frames.append(pd.DataFrame({
            "allwise_cntr": d["allwise_cntr"].to_numpy()[keep].astype("int64"),
            "mjd": d["mjd"].to_numpy()[keep],
            "w1": np.where(q1, d["w1mpro"], np.nan)[keep].astype("float32"),
            "w1e": d["w1sigmpro"].to_numpy()[keep].astype("float32"),
            "w2": np.where(q2, d["w2mpro"], np.nan)[keep].astype("float32"),
            "w2e": d["w2sigmpro"].to_numpy()[keep].astype("float32"),
        }))
        aw.append(d.groupby("allwise_cntr", sort=False)[["w1mpro_allwise", "w2mpro_allwise", "w3mpro_allwise",
                                                         "w4mpro_allwise"]].first())
        del d
    return frames, aw, st


def read_pixel(pixel: int, fs=None, threads: int = 4) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Slim exposure table (cuts applied while streaming, to bound memory) and AllWISE mags per source.
    The 12 yearly files are read concurrently: S3 reads from another cloud are latency-bound."""
    from concurrent.futures import ThreadPoolExecutor

    fs = fs or s3()
    frames, aw, stats = [], [], {"bytes_read": 0, "rows_raw": 0, "releases": 0}
    with ThreadPoolExecutor(threads) as ex:
        for f, a, st in ex.map(lambda rel: _read_release(fs, pixel, rel), RELEASES):
            frames += f
            aw += a
            for k in stats:
                stats[k] += st[k]
    if not frames:
        return pd.DataFrame(), pd.DataFrame(), stats
    allwise = pd.concat(aw).groupby(level=0).first().reset_index()
    return pd.concat(frames, ignore_index=True), allwise, stats


def visits(df: pd.DataFrame) -> pd.DataFrame:
    """Per-source, per-visit medians of W1 and W2 (NaN where a band failed its cuts)."""
    df = df.sort_values(["allwise_cntr", "mjd"], kind="mergesort", ignore_index=True)
    new_src = df["allwise_cntr"].ne(df["allwise_cntr"].shift())
    gap = df["mjd"].diff().gt(VISIT_GAP)
    vid = (new_src | gap).cumsum().to_numpy()
    g = df.groupby(vid, sort=False)
    v = pd.DataFrame({
        "allwise_cntr": g["allwise_cntr"].first(), "t": g["mjd"].median(),
        "w1": g["w1"].median(), "w1_n": g["w1"].count(), "w2": g["w2"].median(), "w2_n": g["w2"].count(),
        "w1_sig": g["w1e"].median(), "w2_sig": g["w2e"].median(),
    })
    for b in ("w1", "w2"):
        dev = (df[b] - v[b].reindex(vid).to_numpy()).abs()
        mad = dev.groupby(vid, sort=False).median() * 1.4826
        n = v[f"{b}_n"].clip(lower=1)
        v[f"{b}_err"] = np.maximum(mad / np.sqrt(n), v[f"{b}_sig"] / np.sqrt(n)).clip(lower=0.005)
    v = v.drop(columns=["w1_sig", "w2_sig"]).reset_index(drop=True)
    return v[(v.w1_n >= 3) & (v.w2_n >= 3)].reset_index(drop=True)


def features(v: pd.DataFrame, allwise: pd.DataFrame) -> pd.DataFrame:
    """One row per star, fully vectorised. Afterglow metric: the largest W2 brightening held for 2
    consecutive visits relative to the first N_BASE visits, with the W1-W2 reddening at those visits."""
    v = v.sort_values(["allwise_cntr", "t"], kind="mergesort", ignore_index=True)
    v["c"] = v.w1 - v.w2
    g = v.groupby("allwise_cntr", sort=False)
    v["rank"] = g.cumcount()
    n = g.size().rename("n_visits")
    base = v[v["rank"] < N_BASE].groupby("allwise_cntr", sort=False).agg(
        w1_base=("w1", "median"), w2_base=("w2", "median"), color_base=("c", "median"), base_std_w2=("w2", "std"))
    agg = g.agg(t_first=("t", "min"), t_last=("t", "max"), w1_ptp=("w1", lambda x: x.max() - x.min()),
                w2_ptp=("w2", lambda x: x.max() - x.min()), w2_med_err=("w2_err", "median"))
    f = pd.concat([n, base, agg], axis=1)
    f["base_scatter_w2"] = np.maximum(f.base_std_w2.fillna(0), f.w2_med_err).clip(lower=0.01)
    v = v.join(f[["w1_base", "w2_base", "color_base"]], on="allwise_cntr")
    v["d1"], v["d2"], v["dc"] = v.w1 - v.w1_base, v.w2 - v.w2_base, v.c - v.color_base
    nxt = v.groupby("allwise_cntr", sort=False)[["d1", "d2", "dc"]].shift(-1)
    pair = v[(v["rank"] >= N_BASE) & nxt.d2.notna()].copy()
    pair["rise2"] = np.minimum(-pair.d2, -nxt.loc[pair.index, "d2"])
    pair["rise1"] = np.minimum(-pair.d1, -nxt.loc[pair.index, "d1"])
    pair["dc2"] = np.minimum(pair.dc, nxt.loc[pair.index, "dc"])
    best = pair.loc[pair.groupby("allwise_cntr", sort=False)["rise2"].idxmax()].set_index("allwise_cntr")
    f["w2_rise"] = best.rise2
    f["w1_rise"] = best.rise1
    f["dcolor_at_rise"] = best.dc2
    f["t_rise"] = best.t
    f["w2_rise_sigma"] = f.w2_rise / f.base_scatter_w2
    last2 = v[v["rank"] >= v.groupby("allwise_cntr")["rank"].transform("max") - 1].groupby("allwise_cntr", sort=False)
    f["w2_end"] = last2.d2.median()
    f["color_end"] = last2.dc.median()
    f = f.reset_index().rename(columns={"index": "allwise_cntr"})
    return f.merge(allwise, on="allwise_cntr", how="left")


def afterglow_flag(f: pd.DataFrame) -> pd.Series:
    """Photospheric before (|W1-W2| < 0.15, quiet), then W2 up >= 0.2 mag and redder by >= 0.1 for 2+ visits."""
    return ((f.n_visits >= 8) & (f.color_base.abs() < 0.15) & (f.base_scatter_w2 < 0.05) & (f.w1_base < 13.5)
            & (f.w2_rise >= 0.2) & (f.dcolor_at_rise >= 0.1) & (f.w2_rise_sigma >= 5))


def positions(pixel: int, cntrs: set, fs=None) -> pd.DataFrame:
    """Second, cheap pass for flagged stars only: median RA/Dec of their detections."""
    fs = fs or s3()
    k0 = pixel >> 10
    parts = []
    want = pa.array(sorted(cntrs), type=pa.int64())
    for rel in RELEASES:
        path = f"{BUCKET}/{rel}/neowiser-healpix_k5-{rel}.parquet/healpix_k0={k0}/healpix_k5={pixel}/part0.snappy.parquet"
        try:
            pf = pq.ParquetFile(fs.open_input_file(path))
        except (FileNotFoundError, OSError):
            continue
        for batch in pf.iter_batches(batch_size=2_000_000, columns=["allwise_cntr", "ra", "dec"]):
            col = pc.cast(batch["allwise_cntr"], pa.int64())
            m = pc.fill_null(pc.is_in(col, value_set=want), False)
            if pc.any(m).as_py():
                parts.append(batch.filter(m).to_pandas())
        if parts and sum(len(x) for x in parts) > 50 * len(cntrs):
            break
    if not parts:
        return pd.DataFrame(columns=["allwise_cntr", "ra", "dec"])
    d = pd.concat(parts)
    return d.groupby("allwise_cntr").agg(ra=("ra", "median"), dec=("dec", "median")).reset_index()


def process(pixel: int, out: str, fs_out=None) -> dict:
    t0 = time.time()
    raw, allwise, st = read_pixel(pixel)
    t1 = time.time()
    if raw.empty:
        return {"pixel": pixel, "status": "empty", **st}
    v = visits(raw)
    f = features(v, allwise)
    f["pixel"] = pixel
    if len(f) and "w2_rise" in f:
        f["afterglow"] = afterglow_flag(f)
        # Keep visit light curves for anything that changed (cheap to store, saves a re-read later).
        keep = f.loc[f.afterglow | ((f.w2_rise.fillna(0) >= 0.15) & (f.w2_rise_sigma.fillna(0) >= 5))
                     | ((f.w1_base < 13) & (f.w2_ptp.fillna(0) >= 0.3)), "allwise_cntr"]
        lc = v[v.allwise_cntr.isin(keep)].assign(pixel=pixel)
        cand = f[f.afterglow].copy()
        if len(cand):
            cand = cand.merge(positions(pixel, set(cand.allwise_cntr.astype("int64"))), on="allwise_cntr", how="left")
    else:
        lc = v.iloc[:0]
        cand = f.iloc[:0]
    t2 = time.time()
    fs, base = (pafs.FileSystem.from_uri(out) if "://" in out else (pafs.LocalFileSystem(), out))
    fs.create_dir(f"{base}/features", recursive=True)
    fs.create_dir(f"{base}/lightcurves", recursive=True)
    fs.create_dir(f"{base}/candidates", recursive=True)
    fs.create_dir(f"{base}/reports", recursive=True)
    pq.write_table(pa.Table.from_pandas(cand, preserve_index=False), f"{base}/candidates/pixel={pixel}.parquet", filesystem=fs)
    pq.write_table(pa.Table.from_pandas(f, preserve_index=False), f"{base}/features/pixel={pixel}.parquet", filesystem=fs)
    pq.write_table(pa.Table.from_pandas(lc, preserve_index=False), f"{base}/lightcurves/pixel={pixel}.parquet", filesystem=fs)
    rep = {"pixel": pixel, "status": "ok", **st, "rows_kept": int(len(raw)), "stars": int(len(f)),
           "afterglow_flags": int(f.get("afterglow", pd.Series(dtype=bool)).sum()), "lc_stars": int(lc.allwise_cntr.nunique()),
           "read_s": round(t1 - t0, 1), "compute_s": round(t2 - t1, 1)}
    with fs.open_output_stream(f"{base}/reports/pixel={pixel}.json") as fh:
        fh.write(json.dumps(rep).encode())
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("pixels", nargs="*", type=int)
    ap.add_argument("--out", required=True)
    ap.add_argument("--task-index", type=int, default=int(os.environ.get("BATCH_TASK_INDEX", "-1")))
    ap.add_argument("--pixels-per-task", type=int, default=48)
    ap.add_argument("--pixel-list", default=None, help="file with one pixel per line (overrides 0..12287)")
    a = ap.parse_args(argv)
    pixels = a.pixels
    if not pixels and a.task_index >= 0:
        allpix = ([int(x) for x in open(a.pixel_list).read().split()] if a.pixel_list else list(range(12288)))
        pixels = allpix[a.task_index * a.pixels_per_task:(a.task_index + 1) * a.pixels_per_task]
    fs, base = (pafs.FileSystem.from_uri(a.out) if "://" in a.out else (pafs.LocalFileSystem(), a.out))
    failed = []
    for p in pixels:
        try:
            if fs.get_file_info(f"{base}/reports/pixel={p}.json").type == pafs.FileType.File:
                print(json.dumps({"pixel": p, "status": "done-before"}), flush=True)
                continue
        except Exception:  # noqa: BLE001
            pass
        for attempt in range(3):
            try:
                print(json.dumps(process(p, a.out)), flush=True)
                break
            except Exception as e:  # noqa: BLE001
                print(json.dumps({"pixel": p, "status": "error", "attempt": attempt, "error": str(e)[:300]}), flush=True)
                time.sleep(10 * (attempt + 1))
        else:
            failed.append(p)
    # Fail loudly so Cloud Batch retries the task; finished pixels are skipped on retry.
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
