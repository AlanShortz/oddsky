"""Hunt H-0004, step 2: light curves for every candidate, cached one file per star, resumable.

  hunts/H-0004/lc/<id>.parquet        ZTF + ATLAS series (oddsky series columns)
  hunts/H-0004/lc/<id>.prov.json      provenance per survey
  hunts/H-0004/lc/atlas_raw/<id>.txt  the ATLAS server's text, so cuts can be re-run without re-queuing

ZTF: IRSA light-curve API (dec > -30), 3 threads. ATLAS: the forced-photometry queue, up to 4 tasks
in flight, task URLs persisted in atlas_tasks.json so a restart picks them up.

  .venv/bin/python scripts/hunt_h0004_fetch.py --surveys ztf,atlas [--limit N] [--ids T20-1,T20-2]
Credentials for ATLAS: ATLAS_TOKEN, or ATLAS_USER + ATLAS_PASSWORD (see ~/.config/oddsky/atlas.env).
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from oddsky.data import atlas, ztf

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("h0004")

here = Path("hunts/H-0004")
lc_dir = here / "lc"
raw_dir = lc_dir / "atlas_raw"
tasks_file = lc_dir / "atlas_tasks.json"


def load_tasks() -> dict:
    return json.loads(tasks_file.read_text()) if tasks_file.exists() else {}


def save_tasks(d: dict) -> None:
    tasks_file.write_text(json.dumps(d, indent=1))


def merge_into(cid: str, key: str, df: pd.DataFrame, prov) -> None:
    """One parquet and one provenance file per star *and survey*, so the ZTF and ATLAS fetchers can run at
    the same time without overwriting each other. The scorer concatenates lc/<id>.*.parquet."""
    pq = lc_dir / f"{cid}.{key}.parquet"
    pj = lc_dir / f"{cid}.{key}.prov.json"
    out = df if not df.empty else pd.DataFrame(columns=["t_mjd", "mag", "err", "band", "survey", "flag"])
    out.to_parquet(pq, index=False)
    pj.write_text(json.dumps(prov.model_dump(), indent=1, default=str))


def have(cid: str, key: str) -> bool:
    return (lc_dir / f"{cid}.{key}.prov.json").exists()


def load_star(cid: str) -> tuple[pd.DataFrame, dict]:
    """All surveys for one star, plus provenance keyed by survey."""
    frames, provs = [], {}
    for pj in lc_dir.glob(f"{cid}.*.prov.json"):
        key = pj.name[len(cid) + 1:-len(".prov.json")]
        provs[key] = json.loads(pj.read_text())
        pq = lc_dir / f"{cid}.{key}.parquet"
        if pq.exists():
            frames.append(pd.read_parquet(pq))
    df = pd.concat([f for f in frames if not f.empty], ignore_index=True) if any(not f.empty for f in frames) else pd.DataFrame()
    return df, provs


# ------------------------------------------------------------------ ZTF
def fetch_ztf(row) -> str:
    if have(row.id, "ztf"):
        return "cached"
    try:
        df, prov = ztf.lightcurve(row.ra, row.dec)
    except Exception as e:  # noqa: BLE001
        log.warning("ZTF %s failed: %s", row.id, str(e)[:100])
        return "failed"
    merge_into(row.id, "ztf", df, prov)
    return f"{prov.status}:{prov.rows_kept}"


# ------------------------------------------------------------------ ATLAS
def atlas_phase(rows: pd.DataFrame, in_flight: int = 4, poll_s: float = 20.0) -> None:
    tasks = load_tasks()  # id -> {"task": url, "result": url|None}
    todo = [r for r in rows.itertuples() if not have(r.id, "atlas") and not (raw_dir / f"{r.id}.txt").exists()]
    # anything with a cached raw file but no parquet entry: just convert
    for r in rows.itertuples():
        raw = raw_dir / f"{r.id}.txt"
        if raw.exists() and not have(r.id, "atlas"):
            df, prov = atlas.lightcurve(r.ra, r.dec, raw_cache=str(raw))
            merge_into(r.id, "atlas", df, prov)
    log.info("ATLAS: %d stars to queue, %d tasks already known", len(todo), len(tasks))
    coords = {r.id: (r.ra, r.dec) for r in rows.itertuples()}
    # only this file's stars: tasks queued for another list (e.g. calibration.csv) are left for that run
    pending = {k: v for k, v in tasks.items() if k in coords and not (raw_dir / f"{k}.txt").exists()}
    queue = iter(todo)
    while True:
        # top up
        while len(pending) < in_flight:
            r = next(queue, None)
            if r is None:
                break
            if r.id in pending:
                continue
            # ATLAS reached full southern cadence in late 2017 and dec < -50 only in 2022: asking for earlier
            # epochs costs server time and returns nothing
            mjd_min = 59500.0 if r.dec < -50 else 58000.0
            try:
                url = atlas.submit(r.ra, r.dec, mjd_min=mjd_min)
            except Exception as e:  # noqa: BLE001
                log.warning("ATLAS submit %s failed: %s", r.id, str(e)[:120])
                time.sleep(30)
                continue
            pending[r.id] = {"task": url, "submitted": time.time()}
            tasks[r.id] = pending[r.id]
            save_tasks(tasks)
            log.info("ATLAS queued %s (%d in flight)", r.id, len(pending))
        if not pending:
            break
        time.sleep(poll_s)
        for cid in list(pending):
            try:
                st = atlas.status(pending[cid]["task"])
            except Exception as e:  # noqa: BLE001
                log.warning("ATLAS status %s: %s", cid, str(e)[:100])
                continue
            if not st.get("finishtimestamp"):
                continue
            raw = raw_dir / f"{cid}.txt"
            raw.parent.mkdir(parents=True, exist_ok=True)
            if st.get("result_url"):
                raw.write_text(atlas.download(st["result_url"]))
            else:
                raw.write_text("")  # finished with no data
            ra, dec = coords[cid]
            df, prov = atlas.lightcurve(ra, dec, raw_cache=str(raw))
            prov.query["task"] = pending[cid]["task"]
            merge_into(cid, "atlas", df, prov)
            log.info("ATLAS done %s: %s %d good", cid, prov.status, prov.rows_kept)
            del pending[cid]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--surveys", default="ztf,atlas")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--ids", default=None, help="comma list of candidate ids")
    ap.add_argument("--file", default="candidates.csv")
    ap.add_argument("--south-first", action="store_true", help="ATLAS: start where ZTF cannot see")
    ap.add_argument("--in-flight", type=int, default=4, help="ATLAS tasks queued at once (be polite)")
    ap.add_argument("--priority", action="store_true", help="ATLAS: best candidates first (see code)")
    a = ap.parse_args()
    lc_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    cand = pd.read_csv(here / a.file)
    if a.ids:
        cand = cand[cand.id.isin(a.ids.split(","))]
    if a.limit:
        cand = cand.head(a.limit)
    surveys = a.surveys.split(",")
    if "ztf" in surveys:
        north = cand[cand.dec > -31]
        log.info("ZTF: %d stars north of -31", len(north))
        with ThreadPoolExecutor(3) as ex:
            for cid, res in zip(north.id, ex.map(fetch_ztf, north.itertuples()), strict=True):
                if res != "cached":
                    log.info("ZTF %s %s", cid, res)
    if "atlas" in surveys:
        if not atlas.available():
            log.error("ATLAS credentials missing: set ATLAS_TOKEN or ATLAS_USER/ATLAS_PASSWORD")
            return
        rows = cand.sort_values("dec") if a.south_first else cand
        if a.priority:
            # Karambelkar+2024 colour group (1-a best) and light-curve class (A = aperiodic variations), their
            # own 8 "RCB-cand" first, then the sky ZTF cannot see.
            col_rank = {"1-a": 0, "2-a": 1, "3-a": 2, "1-b": 3, "2-b": 4, "1-c": 5, "3-b": 6}
            lc_rank = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "G": 6}
            r = cand.copy()
            r["_p"] = (r.get("k24_col_pri", pd.Series("", index=r.index)).map(col_rank).fillna(7)
                       + r.get("k24_lc_pri", pd.Series("", index=r.index)).map(lc_rank).fillna(7)
                       - 20 * r.get("k24_class", pd.Series("", index=r.index)).eq("RCB-cand").astype(int)
                       + 3 * (r.dec > -30).astype(int)
                       # a good parallax that says "dwarf" rules out an R CrB star: last, not never
                       + 10 * ((r.get("poe", pd.Series(0, index=r.index)) > 5) & (r.get("abs_g", pd.Series(-9, index=r.index)) > -1)).astype(int))
            rows = r.sort_values(["_p", "dec"])
        atlas_phase(rows, in_flight=a.in_flight)
    log.info("done")


if __name__ == "__main__":
    main()
