"""Cloud Batch task for hunt H-0012 (mid-IR difference imaging of nearby galaxies). DESIGN: not run.

One task processes a slice of the unWISE tile list. For each tile: fetch the 25 epochal coadds
(2 bands x img/invvar/n) and the bitmask to local disk, run `oddsky.imaging` for every target galaxy
that needs the tile (targets_10mpc.csv from hunts/H-0012/scripts/targets.py), write per-galaxy-tile
outputs to the bucket, delete the bulky difference stacks, write a report. Idempotent: a tile with a
report is skipped, so a preempted or failed job can be resubmitted.

HARD GATE. The epochal coadds live in A. Meisner's personal NERSC web space, with no release, licence
or README. This task refuses to download anything unless the job was submitted with
ODDSKY_UNWISE_PERMISSION=granted (set ONLY after Meisner has agreed to the pull, or after the data were
mirrored somewhere we are allowed to read from, e.g. our own bucket via ODDSKY_UNWISE_EPOCHS=gs-fuse
path). Without it the task exits with status 3 before any network access.

    python imaging_tile.py --tiles tiles.txt --targets targets_10mpc.csv --tiles-per-task 2 \
        --out /mnt/disks/oddsky/runs/h0012 --code-version <git sha>

v2 (run h0012b; hunts/H-0012/reviews/claude-referee-triage-2026-11-01.md):
- galaxy_from_row takes the hand-vetted oddsky.imaging.galaxies entry where one exists (nucleus radius,
  M32/NGC 205 companion masks, centre), the verified centres of targets.py v2 otherwise, neighbouring
  target centres as galaxy cores, and the unWISE bright-source list (--bright) so that bright-star
  footprints that are the galaxy's own light are searched (oddsky.imaging.masks), flagged low-confidence;
- --known: forced photometry at every known transient position in the galaxy's window regardless of
  masks (forced_known.parquet), the recall check;
- report.json carries the per-band mask census (area and light fractions, v1 rule vs v2) per galaxy.

    python imaging_tile.py --tiles tiles.txt --targets targets_10mpc.csv --bright bright_sources_10mpc.csv \
        --known known_positions.csv --tiles-per-task 2 --out /mnt/disks/oddsky/runs/h0012b --code-version <sha>

Outputs per tile: runs/h0012/<tile>/{report.json, <galaxy>/candidates.csv, lightcurves.parquet,
detections.parquet, cutouts.npz, forced_known.parquet}. A merge step (hunts/H-0012/scripts, to write) joins galaxies that
span tiles: candidates within 4" across tiles are the same source; keep the photometry from the tile
where the source is furthest from the window edge (pipeline.photometer's rule).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import numpy as np


def galaxy_from_row(r, targets=None, bright=None):
    """Galaxy for one target row. UNGC has no position angle: a circle of diameter a26 (search_scale 1.2)
    covers any PA. v2: the oddsky.imaging.galaxies entry (acceptance-test nucleus radius, companion masks,
    centre) overrides where one exists; `targets` (the whole table) supplies neighbouring galaxy cores and
    `bright` (bright_sources_10mpc.csv) the unWISE bright-source list with Gaia star verdicts."""
    from oddsky.imaging.galaxies import Galaxy, by_ungc_name

    name = str(r["Name"])
    ra, dec = float(r["ra"]), float(r["dec"])
    nuc = float(min(150.0, max(10.0, 0.04 * r["a26"] * 60)))  # nucleus mask ~4% of the diameter, 10-150"
    extra = ()
    g = by_ungc_name(name)
    if g is not None:
        ra, dec, nuc, extra = g.ra, g.dec, g.nucleus_mask_arcsec, g.extra_masks
    cores = ()
    if targets is not None:
        reach = (1.2 * float(r["a26"]) / 2 + 5.0) / 60  # deg: search radius + window margin
        o = targets[targets.Name != name]
        dd = np.hypot(((o.ra - ra + 180) % 360 - 180) * np.cos(np.radians(dec)), o.dec - dec)
        cores = tuple((float(a), float(b)) for a, b in zip(o.ra[dd < reach], o.dec[dd < reach], strict=True))
    bs = ()
    if bright is not None and len(bright):
        b = bright[bright.galaxy == name]
        bs = tuple((float(a), float(d), float(w), bool(st)) for a, d, w, st in zip(b.ra, b.dec, b.w1mpro.fillna(9.5),
                                                                                     b.is_star.astype(str) == "True", strict=True))
    return Galaxy(name, ra, dec, float(r["a26"]), 1.0, 0.0, float(r["Dist"]), nucleus_mask_arcsec=nuc, search_scale=1.2,
                  extra_masks=extra, cores=cores, bright_sources=bs)


def cutouts(wd: Path, tile: str, cands, h: int = 20) -> dict:
    """41x41 px reference + per-epoch difference cutouts (W1, W2) for candidates with var_sig > 5
    or a stacked-channel detection: enough to re-inspect without the 1 GB stacks."""
    import numpy as np
    from astropy.wcs import WCS

    from oddsky.imaging.pipeline import tile_dir

    out = {}
    sel = cands[(cands.var_sig > 5) | cands.channel.isin(["stack", "both"])]
    for band in (1, 2):
        d = tile_dir(wd, tile, band)
        meta = json.loads((d / "meta.json").read_text())
        w = WCS(meta["wcs"])
        D = np.load(d / "D.npy", mmap_mode="r")
        ref = np.load(d / "ref_s0.npy", mmap_mode="r")
        x, y = w.all_world2pix(sel.ra.to_numpy(), sel.dec.to_numpy(), 0)
        for gid, xi, yi in zip(sel.group, np.round(x).astype(int), np.round(y).astype(int), strict=True):
            if h <= xi < ref.shape[1] - h and h <= yi < ref.shape[0] - h:
                out[f"{gid}_w{band}_ref"] = np.asarray(ref[yi - h:yi + h + 1, xi - h:xi + h + 1], np.float32)
                out[f"{gid}_w{band}_diff"] = np.asarray(D[:, yi - h:yi + h + 1, xi - h:xi + h + 1], np.float32)
    return out


def run_tile(tile: str, targets, out_root: Path, code_version: str, bright=None, known=None, all_targets=None) -> dict:
    import pandas as pd

    from oddsky.imaging import fetch
    from oddsky.imaging.pipeline import (
        Config,
        candidates_from,
        forced_known,
        mask_codes_at,
        photometer,
        process_tile_band,
        recall_summary,
        score,
    )

    t0 = time.time()
    rep = dict(tile=tile, code_version=code_version, pipeline="v2", galaxies={},
               started=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    eps = fetch.list_epochs(tile)
    fetch.fetch_tile(tile, epochs=eps, workers=2)  # <= 2 connections per task; parallelism caps the total
    fetch.fetch_mask(tile)
    rep["epochs"] = eps
    cfg = Config()
    for _, r in targets[targets.tiles.str.contains(tile)].iterrows():
        gal = galaxy_from_row(r, targets if all_targets is None else all_targets, bright)
        wd = Path(tempfile.mkdtemp(prefix="h0012_")) / gal.name
        try:
            dets = pd.concat([process_tile_band(gal, tile, b, wd, cfg) for b in cfg.bands], ignore_index=True)
            cands = candidates_from(dets, cfg)
            lcs = photometer(cands, wd, [tile], cfg.bands) if len(cands) else pd.DataFrame()
            res = score(cands, lcs) if len(cands) else cands
            if len(res):
                res["mask_code"] = mask_codes_at(wd, tile, res.ra.to_numpy(), res.dec.to_numpy())
            dest = out_root / tile / gal.name
            dest.mkdir(parents=True, exist_ok=True)
            res.to_csv(dest / "candidates.csv", index=False)
            dets.to_parquet(dest / "detections.parquet")
            if len(lcs):
                lcs.to_parquet(dest / "lightcurves.parquet")
                np.savez_compressed(dest / "cutouts.npz", **cutouts(wd, tile, res))
            mp = wd / tile / "w1" / "meta.json"  # absent when the galaxy's window holds no usable pixels on this tile
            meta = json.loads(mp.read_text()) if mp.exists() else {}
            census = {}
            for b in cfg.bands:
                mpb = wd / tile / f"w{b}" / "meta.json"
                if mpb.exists():
                    census[f"w{b}"] = json.loads(mpb.read_text()).get("mask_census")
            recall = {}
            kn = known[known.galaxy == gal.name] if known is not None and len(known) else None
            if kn is not None and len(kn) and mp.exists():
                fk = forced_known(kn, wd, tile, cfg.bands)
                if len(fk):
                    fk.to_parquet(dest / "forced_known.parquet")
                    for nm, lc in fk.groupby("name"):
                        disc = pd.to_datetime(str(lc.disc.iloc[0]), errors="coerce")
                        dm = (disc - pd.Timestamp("1858-11-17")) / pd.Timedelta(days=1) if pd.notna(disc) else None
                        recall[nm] = dict(mask=str(lc["mask"].iloc[0]), **{f"w{b}": v for b, v in recall_summary(lc, dm).items()})
            rep["galaxies"][gal.name] = dict(n_detections=len(dets), n_candidates=len(res),
                                             classes=res.cls.value_counts().to_dict() if len(res) else {},
                                             n_low_confidence=int(res.low_confidence.sum()) if "low_confidence" in res else 0,
                                             builds=meta.get("builds"), centre=[gal.ra, gal.dec],
                                             nucleus_mask_arcsec=gal.nucleus_mask_arcsec, extra_masks=list(gal.extra_masks),
                                             n_bright_sources=len(gal.bright_sources), mask_census=census, recall=recall)
        except Exception as e:  # noqa: BLE001  one galaxy must not take down the tile (and the other tile in the task)
            rep["galaxies"][gal.name] = dict(error=f"{type(e).__name__}: {str(e)[:300]}")
        finally:
            shutil.rmtree(wd.parent, ignore_errors=True)  # the D/S stacks (~1 GB per tile-band) never leave the VM
    rep["seconds"] = round(time.time() - t0)
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiles", required=True)
    ap.add_argument("--targets", required=True)
    ap.add_argument("--tiles-per-task", type=int, default=2)
    ap.add_argument("--out", required=True)
    ap.add_argument("--code-version", default="unknown")
    ap.add_argument("--bright", help="bright_sources_10mpc.csv (targets.py v2): unWISE bright sources + Gaia verdicts")
    ap.add_argument("--known", help="known_positions.csv (merge_triage.py known-list): forced photometry, recall check")
    ap.add_argument("--only-galaxies", nargs="*", help="local tests: process only these target names")
    a = ap.parse_args()
    if os.environ.get("ODDSKY_UNWISE_PERMISSION") != "granted":
        print("refusing to fetch: ODDSKY_UNWISE_PERMISSION != granted (ask A. Meisner first; see infra/gcp/README.md)", file=sys.stderr)
        sys.exit(3)
    import pandas as pd

    # the tile cache is ephemeral (deleted after each tile) ONLY when this task chose it: a cache passed in by
    # the caller (e.g. a laptop's ~/oddsky-runs/imaging) is never deleted
    ephemeral = "ODDSKY_IMAGING_CACHE" not in os.environ
    os.environ.setdefault("ODDSKY_IMAGING_CACHE", "/tmp/oddsky-imaging")  # local boot disk, not the bucket
    tiles_all = [t.strip() for t in Path(a.tiles).read_text().split() if t.strip()]
    i = int(os.environ.get("BATCH_TASK_INDEX", "0"))
    mine = tiles_all[i * a.tiles_per_task:(i + 1) * a.tiles_per_task]
    targets = pd.read_csv(a.targets)
    targets = targets[~targets.separate_project.astype(bool)]
    bright = pd.read_csv(a.bright) if a.bright else None
    known = pd.read_csv(a.known, dtype={"name": str}) if a.known else None
    run_targets = targets[targets.Name.isin(a.only_galaxies)] if a.only_galaxies else targets
    out_root = Path(a.out)
    for tile in mine:
        rp = out_root / tile / "report.json"
        if rp.exists():
            continue
        rep = run_tile(tile, run_targets, out_root, a.code_version, bright=bright, known=known, all_targets=targets)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps(rep, indent=1, default=str))
        if ephemeral:
            shutil.rmtree(os.environ["ODDSKY_IMAGING_CACHE"], ignore_errors=True)  # 1 GB per tile


if __name__ == "__main__":
    main()
