"""H-0013 acceptance test: how do OS-0031 and the known extragalactic dust makers / periodic IR sources fare?

    uv run python hunts/H-0013/scripts/known.py

Positions: work/known_dust_makers.json (SIMBAD/literature, compiled 2026-11-02; OS-0031 added here from the H-0012
referee). For each object:

1. the nearest H-0012 merged source within 6" (WISE PSF ~6"): its H-0012 class and the H-0013 scan, verdict and rank;
2. if there is none, why: was the position inside a searched galaxy window, how many >= 5 sigma H-0012 detections
   lie within 6" (by epoch, band and season), and does it fail the candidate rule;
3. where the difference stacks are still on disk (NGC 6946, M31: ~/oddsky-runs/imaging/work/<galaxy>), forced PSF
   photometry at the exact position and the recurrence analysis of that light curve (whatever the candidate rule
   says).

Writes work/acceptance_known.csv and work/acceptance_known.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h0013  # noqa: E402

from oddsky.imaging import metrics, photometry, tiles  # noqa: E402
from oddsky.imaging import recurrence as rc  # noqa: E402

KNOWN = h0013.WORK / "known_dust_makers.json"
OS0031 = dict(name="OS-0031 (NGC 2403 obs#50)", aliases=[], galaxy="NGC 2403", ra=114.22807, dec=65.59806,
              period_d=1940, peaks=[2007.25, 2012.45, 2017.8, 2023.2], category="target (H-0012 discovery)")
LOCAL_WORK = Path("~/oddsky-runs/imaging/work").expanduser()


def sep(ra1, dec1, ra2, dec2):
    return np.hypot((np.asarray(ra1) - ra2) * np.cos(np.radians(dec2)), np.asarray(dec1) - dec2) * 3600


def detections_near(ra, dec, r=6.0):
    """H-0012 run tiles whose window holds the position, the galaxies processed there, and >= 5 sigma detections
    within r arcsec."""
    out = dict(tiles=[], galaxies=[], n_det=0, n_det_epochs=0, seasons=[], max_snr=np.nan, det=[])
    for tdir in sorted(h0013.RUN.glob("*/report.json")):
        tile = tdir.parent.name
        x, y = tiles.wcs_for(tile).all_world2pix(ra, dec, 0)
        if not (0 <= x < tiles.NPIX and 0 <= y < tiles.NPIX):
            continue
        rep = json.loads(tdir.read_text())
        for gal in rep.get("galaxies", {}):
            p = tdir.parent / gal / "detections.parquet"
            if not p.exists():
                continue
            d = pd.read_parquet(p)
            out["tiles"].append(tile)
            out["galaxies"].append(gal)
            if d.empty or "ra" not in d:
                continue
            s = sep(d.ra, d.dec, ra, dec)
            near = d[s < r]
            if len(near):
                out["n_det"] += len(near)
                ep = near[near.channel == "epoch"]
                out["n_det_epochs"] += len(set(zip(ep.band, ep.epoch, strict=False)))
                out["seasons"] = sorted(set(out["seasons"]) | set(ep.season.astype(int)))
                out["max_snr"] = float(np.nanmax([np.nan_to_num(out["max_snr"], nan=-99), near.snr.abs().max()]))
                out["det"] += [f"{c}:W{b}:e{e}:{sn:+.1f}" for c, b, e, sn in zip(near.channel, near.band, near.epoch, near.snr, strict=False)]
    return out


def forced_local(ra, dec):
    """Forced photometry at (ra, dec) on the difference stacks still on disk (NGC 6946, M31)."""
    from astropy.wcs import WCS

    from oddsky.imaging.pipeline import SCALE_BIN, _load_tile

    for gdir in sorted(LOCAL_WORK.glob("*")):
        for tdir in sorted(p for p in gdir.glob("*") if p.is_dir()):
            rows = []
            for band in (1, 2):
                if not (tdir / f"w{band}" / "meta.json").exists():
                    break
                meta, wcs, D, S, scale, psfs, refs = _load_tile(gdir, tdir.name, band)
                x, y = wcs.all_world2pix(ra, dec, 0)
                ny, nx = D.shape[1:]
                if not (13 <= x < nx - 13 and 13 <= y < ny - 13):
                    break
                season = np.array(meta["season"])
                sc = scale[:, min(int(round(float(y))) // SCALE_BIN, scale.shape[1] - 1), min(int(round(float(x))) // SCALE_BIN, scale.shape[2] - 1)]
                f, e = photometry.forced_lightcurve(D, S, psfs, season, float(x), float(y), sc)
                rf = {s: photometry.reference_flux(np.asarray(r), np.asarray(rv), psfs[s], float(x), float(y))[0] for s, (r, rv) in refs.items()}
                rows.append(pd.DataFrame(dict(band=band, epoch=meta["epochs"], mjd=meta["mjd"], season=season, flux=f, err=e,
                                              ref_flux=[rf[int(s)] for s in season])))
            if len(rows) == 2:
                _ = WCS
                return f"{gdir.name}/{tdir.name}", pd.concat(rows, ignore_index=True)
    return None, None


def main():
    known = json.loads(KNOWN.read_text())
    objs = [OS0031] + known
    scan = pd.read_parquet(h0013.OUT / "scan.parquet")
    cands = pd.read_csv(h0013.WORK / "candidates_h0013.csv") if (h0013.WORK / "candidates_h0013.csv").exists() else pd.DataFrame()
    merged = pd.read_parquet(h0013.MERGED, columns=["uid", "galaxy", "ra", "dec", "cls", "var_sig", "what"])
    rows, detail = [], {}
    for o in objs:
        ra, dec = float(o["ra"]), float(o["dec"])
        rec = dict(name=o["name"], galaxy=o["galaxy"], ra=ra, dec=dec, category=o.get("category", ""),
                   lit_period_d=o.get("period_d"), lit_peaks=json.dumps(o.get("peaks") or []))
        s = sep(merged.ra, merged.dec, ra, dec)
        j = int(np.argmin(s))
        rec["nearest_h0012_sep"] = float(s[j])
        if s[j] <= 6.0:
            m = merged.iloc[j]
            rec.update(h0012_uid=m.uid, h0012_cls=m.cls, h0012_var_sig=float(m.var_sig), h0012_what=m.what)
            sc = scan[scan.uid == m.uid]
            if len(sc):
                r = sc.iloc[0]
                rec.update(P_yr=r.P_yr, F=r.F, n_cycles_det=r.n_cycles_det, peaks_det=r.peaks_det, S=r.S, P_sine_d=r.P_sine_d,
                           R=r.R, colour=r.colour, light_verdict=r.light_verdict, light_why=r.light_why)
            if len(cands) and (cands.uid == m.uid).any():
                c = cands[cands.uid == m.uid].iloc[0]
                rec.update(h0013_rank=int(c["rank"]), h0013_verdict=c.verdict, h0013_why=c.why, p_shuffle=c.p_shuffle)
        else:
            dn = detections_near(ra, dec)
            rec.update(searched_tiles=",".join(sorted(set(dn["tiles"]))), searched_galaxies=",".join(sorted(set(dn["galaxies"]))),
                       n_det_6as=dn["n_det"], n_det_epoch_band=dn["n_det_epochs"], det_seasons=json.dumps(dn["seasons"]),
                       det_max_snr=dn["max_snr"], det_list=";".join(dn["det"][:12]))
        where, lc = forced_local(ra, dec)
        if lc is not None:
            L = rc.from_long(lc, metrics.align_seasons)
            a = rc.analyse(L)
            v, why = rc.light_verdict(a)
            null = rc.shuffle_null(L, 200, seed=1)
            rec.update(forced_where=where, forced_P_yr=a["P_yr"], forced_F=a["F"], forced_n_cycles=a["n_cycles_det"],
                       forced_peaks=json.dumps(a["peaks_det"]), forced_verdict=v, forced_why=",".join(why),
                       forced_p_shuffle=rc.p_value(null, a["F"]), forced_amp_w2_ujy=a["amp_w2"] * 0.171787,
                       forced_med_err_w2_ujy=float(np.nanmedian(L.e[1])) * 0.171787)
            detail[o["name"]] = dict(t=L.t.round(3).tolist(), w1=L.y[0].round(1).tolist(), w2=L.y[1].round(1).tolist(),
                                     e1=L.e[0].round(1).tolist(), e2=L.e[1].round(1).tolist())
        rows.append(rec)
        print(f"{o['name'][:30]:30s} sep {rec['nearest_h0012_sep']:7.1f}\"  {rec.get('h0012_cls', '-'):14s} "
              f"{rec.get('light_verdict', '-'):10s} rank {rec.get('h0013_rank', '-')}  forced {rec.get('forced_verdict', '-')}", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(h0013.WORK / "acceptance_known.csv", index=False)
    (h0013.WORK / "acceptance_known.json").write_text(json.dumps(dict(forced_lightcurves=detail), indent=1))


if __name__ == "__main__":
    main()
