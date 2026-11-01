"""H-0012 target list: star-forming galaxies within 10 Mpc, and the unWISE tiles they need.

    uv run python hunts/H-0012/scripts/targets.py [--dmax 10] [--logsfr-min -2.5] [--amin 1.0]

Source: the Updated Nearby Galaxy Catalog (UNGC; Karachentsev, Makarov & Kaisina 2013, AJ 145, 101),
VizieR J/AJ/145/101/catalog, fetched as ASU-TSV from a VizieR mirror (vizier.idia.ac.za, falling back to
vizier.cfa.harvard.edu and CDS; CDS itself was timing out on 2026-11-01). The raw table is cached in
~/oddsky-runs/imaging/meta/ungc_J_AJ_145_101.tsv with the URL and date in a sidecar .json.

Star formation rate (Karachentsev & Kaisina 2013, AJ 146, 46, eqs. 1-2; D in Mpc):
    log SFR(FUV) = 2.78 - 0.4 m_FUV^c + 2 log D,   m_FUV^c = FUV - 1.93 A_B   (Galactic only)
    log SFR(Ha)  = 3.54 - 0.4 m_Ha^c  + 2 log D,   m_Ha^c  = Hamag - 0.538 A_B
(UNGC defines m_Ha = -2.5 log F(Ha) - 13.6 with F in erg/s/cm^2; with SFR = 7.9e-42 L(Ha), Kennicutt
1998, log SFR = log F + 2 log D + 8.98 = 3.54 - 0.4 m_Ha + 2 log D. Check: M33 gives log SFR(FUV) =
-0.5, LMC log SFR(Ha) = -0.6.)
Internal extinction is not corrected (SFRs are lower limits; the cut is conservative). Limits
(l_FUV / l_Hamag = '>') count as non-detections. A galaxy is star-forming if either SFR >= the cut.
UNGC has NO FUV or Ha flux for some of the biggest galaxies (M31, LMC, SMC) and for galaxies behind
the Milky Way plane; with no SFR measurement a galaxy is kept if it is a late type (T = 1-10,
Sa-Im) with M_B <= -14 (column sfr_basis = 'type').

Cuts: D <= dmax; log SFR >= logsfr_min (default -2.5, i.e. 0.003 Msun/yr); a26 >= amin arcmin
(galaxies smaller than ~1' are a few WISE PSFs across). The Milky Way satellites LMC and SMC are
listed but flagged 'separate project' (tens of tiles each). UNGC has no position angle, so the
search region per galaxy is a CIRCLE of diameter 1.2 x a26 (conservative: covers any PA).
Writes work/targets_10mpc.csv and work/targets_10mpc_summary.json.
"""

from __future__ import annotations

import argparse
import io
import json
import time
from pathlib import Path

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord

from oddsky.data.http import request
from oddsky.imaging import fetch, tiles

HERE = Path(__file__).resolve().parents[1]
MIRRORS = ("vizier.idia.ac.za", "vizier.cfa.harvard.edu", "vizier.cds.unistra.fr")
SEPARATE = {"LMC", "SMC"}


def fetch_ungc() -> tuple[pd.DataFrame, dict]:
    cache = fetch.cache_root() / "meta" / "ungc_J_AJ_145_101.tsv"
    side = cache.with_suffix(".json")
    if not cache.exists():
        last = None
        for host in MIRRORS:
            url = f"https://{host}/viz-bin/asu-tsv?-source=J/AJ/145/101/catalog&-out.max=unlimited&-out.all"
            try:
                text = request("GET", url, timeout=180, retries=2).text
                if "Name" in text:
                    cache.parent.mkdir(parents=True, exist_ok=True)
                    cache.write_text(text)
                    side.write_text(json.dumps(dict(url=url, fetched=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))))
                    break
            except Exception as e:  # try the next mirror
                last = e
        else:
            raise RuntimeError(f"UNGC unavailable from all mirrors: {last}")
    lines = [ln for ln in cache.read_text().splitlines() if ln and not ln.startswith("#")]
    head = lines[0].split("\t")
    body = [ln for ln in lines[3:] if ln.split("\t")[0].strip().isdigit()]  # skip units/dashes rows
    df = pd.read_csv(io.StringIO("\n".join(["\t".join(head)] + body)), sep="\t", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    for c in df.columns:
        df[c] = df[c].str.strip()
    num = ["a26", "b/a", "AB", "FUV", "Bmag", "Hamag", "Kmag", "TT", "Dist", "BMag", "KLum", "M26", "MHI"]
    for c in num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df, json.loads(side.read_text())


def sfr(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    logd = 2 * np.log10(df.Dist)
    fuv_ok = df.FUV.notna() & (df.l_FUV != ">")
    ha_ok = df.Hamag.notna() & (df.l_Hamag != ">")
    s_fuv = np.where(fuv_ok, 2.78 - 0.4 * (df.FUV - 1.93 * df.AB.fillna(0)) + logd, np.nan)
    s_ha = np.where(ha_ok, 3.54 - 0.4 * (df.Hamag - 0.538 * df.AB.fillna(0)) + logd, np.nan)
    return pd.Series(s_fuv, index=df.index), pd.Series(s_ha, index=df.index)


def _primary(ras, decs) -> list[str]:
    """Primary tile (nearest centre: unWISE's own de-duplication) of every point."""
    t = tiles.tile_table()
    tra, tdec = np.radians(np.asarray(t["ra"], float)), np.radians(np.asarray(t["dec"], float))
    tv = np.c_[np.cos(tdec) * np.cos(tra), np.cos(tdec) * np.sin(tra), np.sin(tdec)]
    ra, dec = np.radians(ras), np.radians(decs)
    pv = np.c_[np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)]
    ids = np.asarray(t["coadd_id"])
    return sorted({str(ids[np.argmax(tv @ v)]) for v in pv})


def tiles_for(ra: float, dec: float, diam_arcmin: float) -> list[str]:
    r = diam_arcmin / 2 / 60
    t = np.linspace(0, 2 * np.pi, 72, endpoint=False)
    ras = np.r_[ra, ra + r * np.cos(t) / np.cos(np.radians(dec))]
    decs = np.r_[dec, dec + r * np.sin(t)]
    if r > 0.5:  # fill big discs too (tiles are 1.56 deg)
        g = np.arange(-r, r + 0.25, 0.25)
        gx, gy = np.meshgrid(g, g)
        inside = np.hypot(gx, gy) <= r
        ras = np.r_[ras, ra + gx[inside] / np.cos(np.radians(dec))]
        decs = np.r_[decs, dec + gy[inside]]
    return _primary(ras % 360, np.clip(decs, -90, 90))


def main(dmax=10.0, logsfr_min=-2.5, amin=1.0, scale=1.2):
    df, prov = fetch_ungc()
    c = SkyCoord(df.RAJ2000.values, df.DEJ2000.values, unit=(u.hourangle, u.deg))
    df["ra"], df["dec"] = c.ra.deg, c.dec.deg
    df["logSFR_FUV"], df["logSFR_Ha"] = sfr(df)
    df["logSFR"] = df[["logSFR_FUV", "logSFR_Ha"]].max(axis=1)
    by_type = df.logSFR.isna() & df.TT.between(1, 10) & (df.BMag <= -14)
    df["sfr_basis"] = np.where(df.logSFR.notna(), "FUV/Ha", np.where(by_type, "type", ""))
    sf = (df.logSFR >= logsfr_min) | by_type
    sel = (df.Dist <= dmax) & sf & (df.a26 >= amin) & (df.Name != "Milky Way")
    t = df[sel].copy()
    t["separate_project"] = t.Name.isin(SEPARATE)
    t["search_diam_arcmin"] = scale * t.a26
    t["tiles"] = [",".join(tiles_for(r.ra, r.dec, r.search_diam_arcmin)) if not r.separate_project else ""
                  for r in t.itertuples()]
    t["n_tiles"] = [len(x.split(",")) if x else 0 for x in t.tiles]
    cols = ["Name", "ra", "dec", "Dist", "f_Dist", "a26", "b/a", "TT", "BMag", "logSFR_FUV", "logSFR_Ha", "logSFR", "sfr_basis",
            "search_diam_arcmin", "n_tiles", "tiles", "separate_project"]
    t = t[cols].sort_values("Dist").reset_index(drop=True)
    out = HERE / "work" / "targets_10mpc.csv"
    t.to_csv(out, index=False)
    uniq = sorted({x for s in t.tiles for x in s.split(",") if x})
    summary = dict(
        source="UNGC, Karachentsev, Makarov & Kaisina 2013, AJ 145, 101 (VizieR J/AJ/145/101)", provenance=prov,
        n_ungc=int(len(df)), n_within_dmax=int((df.Dist <= dmax).sum()),
        n_sf_within_dmax=int(((df.Dist <= dmax) & sf & (df.Name != "Milky Way")).sum()),
        n_targets_sfr_from_type=int((t.sfr_basis == "type").sum()),
        n_targets=int(len(t)), n_separate_project=int(t.separate_project.sum()),
        n_unique_tiles=len(uniq),
        separate_project_tiles={r.Name: len(tiles_for(r.ra, r.dec, r.search_diam_arcmin)) for r in t[t.separate_project].itertuples()},
        cuts=dict(dmax_mpc=dmax, logsfr_min=logsfr_min, a26_min_arcmin=amin, search_scale=scale),
        n_by_distance={f"<{d}": int((t.Dist < d).sum()) for d in (1, 2, 4, 6, 8, 10.01)},
        largest=t.sort_values("n_tiles", ascending=False).head(8)[["Name", "Dist", "a26", "n_tiles"]].to_dict("records"),
        estimated_input_gb=round(len(uniq) * 1.0, 0),
    )
    (HERE / "work" / "targets_10mpc_summary.json").write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps(summary, indent=1, default=str))
    print("wrote", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dmax", type=float, default=10.0)
    ap.add_argument("--logsfr-min", type=float, default=-2.5)
    ap.add_argument("--amin", type=float, default=1.0)
    a = ap.parse_args()
    main(a.dmax, a.logsfr_min, a.amin)
